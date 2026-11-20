import numpy as np
class R: pass
def OLS(y,X):
    y=np.asarray(y,float); X=np.asarray(X,float)
    b,*_=np.linalg.lstsq(X,y,rcond=None); res=y-X@b
    r=R(); r.params=b; r.rsquared=1-res.var()/y.var(); n,k=X.shape
    s2=res@res/(n-k); r.bse=np.sqrt(np.diag(s2*np.linalg.pinv(X.T@X))); return r
def add_constant(X):
    X=np.asarray(X,float); X=X.reshape(len(X),-1); return np.column_stack([np.ones(len(X)),X])
