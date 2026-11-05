"""Educational 3D Euler-Bernoulli frame finite elements + compression eigenbuckling.
Six DOF/node (u,v,w,rx,ry,rz); no rotor transport or Maxwell coupling.
Prestress is imposed, NOT derived from verified equilibrium. No design certification.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import eig

@dataclass(frozen=True)
class Section:
    E: float = 200e9
    G: float = 77e9
    A: float = .01
    Iy: float = .00001
    Iz: float = .00001
    J: float = .00002
    def __post_init__(self):
        if min(self.E,self.G,self.A,self.Iy,self.Iz,self.J) <= 0:
            raise ValueError('positive section inputs required')

class FrameElement:
    def __init__(self,a,b,section:Section=Section()):
        self.a=np.asarray(a,dtype=float);self.b=np.asarray(b,dtype=float);self.section=section
        axis=self.b-self.a;self.L=float(np.linalg.norm(axis))
        if self.L<=0:raise ValueError('nonzero element length required')
        x=axis/self.L;ref=np.array([0.,0.,1.])
        if abs(x@ref)>.9:ref=np.array([0.,1.,0.])
        y=np.cross(ref,x);y/=np.linalg.norm(y);z=np.cross(x,y)
        R=np.array([x,y,z]);self.T=np.zeros((12,12))
        for k in range(4):self.T[3*k:3*k+3,3*k:3*k+3]=R

    def stiffness_local(self):
        p=self.section;L=self.L;k=np.zeros((12,12))
        def block(indices,mat):k[np.ix_(indices,indices)]+=mat
        block([0,6],p.E*p.A/L*np.array([[1,-1],[-1,1]]))
        block([3,9],p.G*p.J/L*np.array([[1,-1],[-1,1]]))
        for ids,EI,sgn in [([1,5,7,11],p.E*p.Iz,1),([2,4,8,10],p.E*p.Iy,-1)]:
            q=np.array([[12,6*L*sgn,-12,6*L*sgn],
                        [6*L*sgn,4*L*L,-6*L*sgn,2*L*L],
                        [-12,-6*L*sgn,12,-6*L*sgn],
                        [6*L*sgn,2*L*L,-6*L*sgn,4*L*L]])
            block(ids,EI/L**3*q)
        return k

    def geometric_local(self,axial_force):
        """Consistent initial-stress tangent using cubic Hermite transverse shapes.
        Positive axial_force is tension: adds stiffness; negative is compression.
        """
        L=self.L;kg=np.zeros((12,12));a=float(axial_force)
        for ids,sgn in [([1,5,7,11],1),([2,4,8,10],-1)]:
            M=np.array([[36,3*L*sgn,-36,3*L*sgn],
                        [3*L*sgn,4*L*L,-3*L*sgn,-L*L],
                        [-36,-3*L*sgn,36,-3*L*sgn],
                        [3*L*sgn,-L*L,-3*L*sgn,4*L*L]])
            kg[np.ix_(ids,ids)]+=a/(30*L)*M
        return kg

    def matrices(self,axial_force=0):
        t=self.T
        return t.T@self.stiffness_local()@t,t.T@self.geometric_local(axial_force)@t

def circular_arc(radius=100.,sweep=np.pi/2,elements=12):
    if radius<=0 or elements<2 or sweep<=0 or sweep>2*np.pi:
        raise ValueError('invalid geometry')
    a=np.linspace(0,sweep,elements+1)
    return np.column_stack((radius*np.cos(a),radius*np.sin(a),np.zeros(len(a))))

def assemble(nodes,section=Section(),reference_axial_force=-1.):
    nodes=np.asarray(nodes,dtype=float);n=len(nodes)
    K=np.zeros((n*6,n*6));KG=K.copy()
    for i in range(n-1):
        e=FrameElement(nodes[i],nodes[i+1],section)
        ke,ge=e.matrices(reference_axial_force)
        ix=np.arange(i*6,(i+2)*6)
        K[np.ix_(ix,ix)]+=ke;KG[np.ix_(ix,ix)]+=ge
    return K,KG

def buckling(nodes,section=Section(),load_n=1e5,both_ends_fixed=True):
    """Compute lowest positive linearized compression load multiplier.
    For imposed negative load_n reference stress: det(K + lambda KG)=0.
    """
    if load_n<=0:raise ValueError('reference compression magnitude must be positive')
    K,KG=assemble(nodes,section,-load_n)
    total=K.shape[0];fixed=list(range(6))
    if both_ends_fixed:fixed+=list(range(total-6,total))
    free=np.setdiff1d(np.arange(total),fixed)
    A=K[np.ix_(free,free)];B=-KG[np.ix_(free,free)]
    vals,vecs=eig(A,B,check_finite=True)
    acceptable=np.flatnonzero(np.isfinite(vals)&
        (abs(vals.imag)<1e-6*np.maximum(1,abs(vals.real)))&(vals.real>1e-10))
    if not len(acceptable):
        return {'status':'NO_POSITIVE_MODE','critical_factor':None}
    j=acceptable[np.argmin(vals[acceptable].real)]
    lam=float(vals[j].real);mode=vecs[:,j].real
    residual=float(np.linalg.norm((A-lam*B)@mode)/
        (np.linalg.norm(A@mode)+np.linalg.norm(lam*B@mode)+1e-30))
    return {'status':'NUMERICAL_MODE','critical_factor':lam,'critical_force_n':lam*load_n,
            'residual':residual,'free_dof':len(free),'elements':len(nodes)-1,
            'assumptions':['fixed-end linearized static compression',
                           'undeformed circular chord frames','no gyroscopic transport',
                           'no nonlinear postbuckling','not orbital-ring validation']}
