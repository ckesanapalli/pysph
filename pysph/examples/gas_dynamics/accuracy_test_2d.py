"""Acoustic wave diffusion in 2-d (2 mins)

Two Dimensional constant pressure accuracy test
particles should simply advect in a periodic domain
"""

# NumPy and standard library imports
import numpy

from pysph.base.nnps import DomainManager
from pysph.base.utils import get_particle_array as gpa
from pysph.solver.application import Application

from pysph.sph.scheme import GasDScheme, ADKEScheme, GSPHScheme, SchemeChooser

# PySPH tools
from pysph.tools import uniform_distribution as ud

# Numerical constants
dim = 2
gamma = 1.4
gamma1 = gamma - 1.0

# solution parameters
dt = 5e-3
tf = 1.


# domain size
xmin = 0.
xmax = 1.
ymin = 0.
ymax = 1.


# scheme constants
alpha1 = 1.0
alpha2 = 0.1
beta = 2.0
kernel_factor = 1.5


class AccuracyTest2D(Application):
    def initialize(self):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.ny = 100
        self.nx = self.ny
        self.dx = (self.xmax - self.xmin) / (self.nx)
        self.hdx = 2.
        self.p = 1.
        self.u = 1
        self.v = -1

    def create_domain(self):
        return DomainManager(
            xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
            periodic_in_x=True, periodic_in_y=True)

    def create_particles(self):
        global dx
        data = ud.uniform_distribution_cubic2D(
            self.dx, xmin, xmax, ymin, ymax
            )

        x = data[0].ravel()
        y = data[1].ravel()
        dx = data[2]

        volume = dx * dx

        rho = 1 + 0.2 * numpy.sin(
            numpy.pi * (x + y)
        )

        p = numpy.ones_like(x) * self.p

        # const h and mass
        h = numpy.ones_like(x) * self.hdx * dx
        m = numpy.ones_like(x) * volume * rho

        # u = 1
        u = numpy.ones_like(x) * self.u

        # v = -1
        v = numpy.ones_like(x) * self.v

        # thermal energy from the ideal gas EOS
        e = p/(gamma1*rho)

        fluid = gpa(name='fluid', x=x, y=y, rho=rho, p=p, e=e, h=h, m=m,
                    h0=h.copy(), u=u, v=v)
        self.scheme.setup_properties([fluid])

        print("2D Accuracy Test with %d particles"
              % (fluid.get_number_of_particles()))

        return [fluid, ]

    def create_scheme(self):
        self.dt = dt
        self.tf = tf

        adke = ADKEScheme(
            fluids=['fluid'], solids=[], dim=dim, gamma=gamma,
            alpha=1, beta=1, k=1.0, eps=0.8, g1=0.5, g2=0.5)

        mpm = GasDScheme(
            fluids=['fluid'], solids=[], dim=dim, gamma=gamma,
            kernel_factor=kernel_factor, alpha1=alpha1, alpha2=alpha2,
            beta=beta
        )

        gsph = GSPHScheme(
            fluids=['fluid'], solids=[], dim=dim, gamma=gamma,
            kernel_factor=1.,
            g1=0., g2=0., rsolver=2, interpolation=0, monotonicity=0,
            interface_zero=True, hybrid=False, blend_alpha=5.0,
            niter=40, tol=1e-6
        )

        s = SchemeChooser(
            default='gsph', adke=adke, mpm=mpm, gsph=gsph
        )
        return s

    def configure_scheme(self):
        s = self.scheme
        if self.options.scheme == 'mpm':
            s.configure(kernel_factor=kernel_factor)
            s.configure_solver(dt=self.dt, tf=self.tf,
                               adaptive_timestep=True, pfreq=50)
        elif self.options.scheme == 'adke':
            s.configure_solver(dt=self.dt, tf=self.tf,
                               adaptive_timestep=False, pfreq=50)
        elif self.options.scheme == 'gsph':
            s.configure_solver(dt=self.dt, tf=self.tf,
                               adaptive_timestep=False, pfreq=50)

    def post_process(self):
        from pysph.solver.utils import load
        if len(self.output_files) < 1:
            return
        outfile = self.output_files[-1]
        data = load(outfile)
        pa = data['arrays']['fluid']
        x_c = pa.x
        y_c = pa.y
        rho_c = pa.rho
        rho_e = 1 + 0.2 * numpy.sin(
            numpy.pi * (x_c + y_c)
        )
        num_particles = rho_c.size
        l1_norm = numpy.sum(
            numpy.abs(rho_c - rho_e)
        ) / num_particles

        print(l1_norm)


if __name__ == '__main__':
    app = AccuracyTest2D()
    app.run()
    app.post_process()