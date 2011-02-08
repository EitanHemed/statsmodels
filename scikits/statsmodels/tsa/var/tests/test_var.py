"""
Test VAR Model
"""

from cStringIO import StringIO
import nose
import os
import sys

import numpy as np
import matplotlib.pyplot as plt

import scikits.statsmodels.api as sm
import scikits.statsmodels.tsa.var.model as model
import scikits.statsmodels.tsa.var.util as util
reload(model)
from scikits.statsmodels.tsa.var.model import VAR

from numpy.testing import assert_almost_equal, assert_equal

DECIMAL_6 = 6
DECIMAL_5 = 5
DECIMAL_4 = 4
DECIMAL_3 = 3
DECIMAL_2 = 2

basepath = os.path.split(sm.__file__)[0]
resultspath = basepath + '/tsa/var/tests/results/'

def test_lutkepohl_parse():
    lut_data = basepath + '/tsa/var/data/'
    files = [lut_data + 'e%d.dat' % i for i in range(1, 7)]

    try:
        import pandas
    except ImportError:
        raise nose.SkipTest

    for f in files:
        util.parse_lutkepohl_data(f)

class CheckVAR(object):

    def test_params(self):
        assert_almost_equal(self.res1.params, self.res2.params, DECIMAL_3)

    def test_neqs(self):
        assert_equal(self.res1.neqs, self.res2.neqs)

    def test_nobs(self):
        assert_equal(self.res1.avobs, self.res2.nobs)

    def test_df_eq(self):
        assert_equal(self.res1.df_eq, self.res2.df_eq)

    def test_rmse(self):
        results = self.res1.results
        for i in range(len(results)):
            assert_almost_equal(results[i].mse_resid**.5,
                    eval('self.res2.rmse_'+str(i+1)), DECIMAL_6)

    def test_rsquared(self):
        results = self.res1.results
        for i in range(len(results)):
            assert_almost_equal(results[i].rsquared,
                    eval('self.res2.rsquared_'+str(i+1)), DECIMAL_3)

    def test_llf(self):
        results = self.res1.results
        assert_almost_equal(self.res1.llf, self.res2.llf, DECIMAL_2)
        for i in range(len(results)):
            assert_almost_equal(results[i].llf,
                    eval('self.res2.llf_'+str(i+1)), DECIMAL_2)

    def test_aic(self):
        assert_almost_equal(self.res1.aic, self.res2.aic)

    def test_bic(self):
        assert_almost_equal(self.res1.bic, self.res2.bic)

    def test_hqic(self):
        assert_almost_equal(self.res1.hqic, self.res2.hqic)

    def test_fpe(self):
        assert_almost_equal(self.res1.fpe, self.res2.fpe)

    def test_detsig(self):
        assert_almost_equal(self.res1.detomega, self.res2.detsig)

    def test_bse(self):
        assert_almost_equal(self.res1.bse, self.res2.bse, DECIMAL_4)

def get_macrodata():
    data = sm.datasets.macrodata.load().data[['realgdp','realcons','realinv']]
    names = data.dtype.names
    data = data.view((float,3))
    data = np.diff(np.log(data), axis=0)
    return data, names

def generate_var():
    from rpy2.robjects import r
    import pandas.rpy.common as prp
    r.source('tests/var.R')
    return prp.convert_robj(r['result'], use_pandas=False)

def write_generate_var():
    result = generate_var()
    np.savez('tests/results/vars_results.npz', **result)

class RResults(object):
    """
    Simple interface with results generated by "vars" package in R.
    """

    def __init__(self):
        data = np.load(resultspath + 'vars_results.npz')

        self.names = data['coefs'].dtype.names
        self.params = data['coefs'].view((float, len(self.names)))
        self.stderr = data['stderr'].view((float, len(self.names)))

        self.irf = data['irf'].item()
        self.orth_irf = data['orthirf'].item()

        self.nirfs = int(data['nirfs'][0])
        self.nobs = int(data['obs'][0])
        self.totobs = int(data['totobs'][0])

        crit = data['crit'].item()
        self.aic = crit['aic'][0]
        self.sic = self.bic = crit['sic'][0]
        self.hqic = crit['hqic'][0]
        self.fpe = crit['fpe'][0]

        self.detomega = data['detomega'][0]
        self.loglike = data['loglike'][0]

        self.nahead = int(data['nahead'][0])
        self.ma_rep = data['phis']

# half-baked attempt

_monkeypatched_mpl = False
_draw_function = None

def _suppress_plots():

    global _monkeypatched_mpl, _draw_function
    if not _monkeypatched_mpl:
        _draw_function = plt.draw_if_interactive
        plt.draw_if_interactive = lambda *args, **kwargs: None

def _unsuppress_plots():
    plt.draw_if_interactive = _draw_function

class CheckIRF(object):

    def test_irf_coefs(self):
        self._check_irfs(self.irf.irfs, self.ref.irf)
        self._check_irfs(self.irf.orth_irfs, self.ref.orth_irf)

    def _check_irfs(self, py_irfs, r_irfs):
        for i, name in enumerate(self.res.names):
            ref_irfs = r_irfs[name].view((float, self.k))
            res_irfs = py_irfs[:, :, i]
            assert_almost_equal(ref_irfs, res_irfs)

    def test_plot_irf(self):
        self.irf.plot()
        self.irf.plot(impulse=0, response=1)

    def test_plot_cum_effects(self):
        self.irf.plot_cum_effects()
        self.irf.plot_cum_effects(impulse=0, response=1)

class TestVARResults(CheckIRF):

    def __init__(self):
        self.p = 2

        data, names = get_macrodata()
        self.ref = RResults()
        self.model = VAR(data, names=names)
        self.res = self.model.fit(maxlags=self.p)
        self.irf = self.res.irf(self.ref.nirfs)
        self.nahead = self.ref.nahead
        self.k = len(self.ref.names)

    def test_aaamonkeypatches(self):
        sys.stdout = StringIO()

    def test_zzzundomonkeypatches(self):
        sys.stdout = sys.__stdout__

    def test_params(self):
        assert_almost_equal(self.res.params, self.ref.params, DECIMAL_3)

    def test_detsig(self):
        assert_almost_equal(self.res.detomega, self.ref.detomega)

    def test_aic(self):
        assert_almost_equal(self.res.aic, self.ref.aic)

    def test_bic(self):
        assert_almost_equal(self.res.bic, self.ref.bic)

    def test_hqic(self):
        assert_almost_equal(self.res.hqic, self.ref.hqic)

    def test_fpe(self):
        assert_almost_equal(self.res.fpe, self.ref.fpe)

    def test_nobs(self):
        assert_equal(self.res.nobs, self.ref.nobs)

    def test_stderr(self):
        assert_almost_equal(self.res.stderr, self.ref.stderr, DECIMAL_4)

    def test_loglike(self):
        assert_almost_equal(self.res.loglike, self.ref.loglike)

    def test_ma_rep(self):
        ma_rep = self.res.ma_rep(self.nahead)
        assert_almost_equal(ma_rep, self.ref.ma_rep)

    #--------------------------------------------------
    # Lots of tests to make sure stuff works...need to check correctness

    def test_causality(self):
        pass

    def test_select_order(self):
        result = self.model.fit(10, ic='aic', verbose=True)
        result = self.model.fit(10, ic='fpe', verbose=True)

    def test_is_stable(self):
        # may not necessarily be true for other datasets
        assert(self.res.is_stable())

    def test_acf(self):
        # test that it works...for now
        acfs = self.res.acf(10)

    def test_acorr(self):
        acorrs = self.res.acorr(10)

    def test_plot_acorr(self):
        self.res.plot_acorr()

    def test_forecast(self):
        point = self.res.forecast(self.res.y[-5:], 5)

    def test_forecast_interval(self):
        point, lower, upper = self.res.forecast_interval(5)

    def test_plot_forecast(self):
        self.res.plot_forecast(5)

    # def test_neqs(self):
    #     assert_equal(self.res1.neqs, self.res2.neqs)

    # def test_df_eq(self):
    #     assert_equal(self.res1.df_eq, self.res2.df_eq)

if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__,'-vvs','-x','--pdb', '--pdb-failure'],
                   exit=False)
