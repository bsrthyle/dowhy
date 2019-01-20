import numpy as np
from sklearn import linear_model
import pandas as pd
from dowhy.causal_estimator import CausalEstimate
from dowhy.causal_estimator import CausalEstimator
import logging


class GFormulaEstimator(CausalEstimator):
    """Compute effect of treatment using linear regression and the Robins G-Formula.

    The coefficient of the treatment variable in the regression model is
    computed as the causal effect. Common method but the assumptions required
    are too strong. Avoid.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger.debug("Back-door variables used:" +
                          ",".join(self._target_estimand.backdoor_variables))
        self._observed_common_causes_names = self._target_estimand.backdoor_variables
        self._observed_common_causes = self._data[self._observed_common_causes_names]
        self._observed_common_causes = pd.get_dummies(self._observed_common_causes, drop_first=True)
        self.logger.info("INFO: Using Linear Robins G-Formula Estimator")
        self.symbolic_estimator = self.construct_symbolic_estimator(self._target_estimand)
        self.logger.info(self.symbolic_estimator)
        self._linear_model = None

    def _build_linear_model(self):
        treatment_2d = self._treatment.values.reshape(len(self._treatment), -1)
        features = np.concatenate((treatment_2d, self._observed_common_causes),
                                  axis=1)
        model = linear_model.LinearRegression()
        model.fit(features, self._outcome)
        self._linear_model = model

    def _estimate_effect(self):
        if not self._linear_model:
            self._build_linear_model()
        coefficients = self._linear_model.coef_
        self.logger.debug("Coefficients of the fitted linear model: " +
                          ",".join(map(str, coefficients)))
        estimate = CausalEstimate(estimate=coefficients[0],
                                  target_estimand=self._target_estimand,
                                  realized_estimand_expr=self.symbolic_estimator,
                                  intercept=self._linear_model.intercept_)
        return estimate

    def _do(self, x):
        if not self._linear_model:
            self._build_linear_model()
        interventional_treatment_2d = np.full(self._treatment.shape, x).reshape(len(self._treatment), -1)
        features = np.concatenate((interventional_treatment_2d, self._observed_common_causes),
                                  axis=1)
        interventional_outcomes = self._linear_model.predict(features)
        return interventional_outcomes.mean()

    def construct_symbolic_estimator(self, estimand):
        expr = "b: " + estimand.outcome_variable + "~"
        var_list = [estimand.treatment_variable, ] + estimand.backdoor_variables
        expr += "+".join(var_list)
        return expr
