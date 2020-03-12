import dowhy.datasets
from dowhy import CausalModel
import logging

class TestRefuter(object):
    def __init__(self, error_tolerance, estimator_method, refuter_method,
            confounders_effect_on_t=None, confounders_effect_on_y=None,
            effect_strength_on_t=None, effect_strength_on_y=None, **kwargs):
        self._error_tolerance = error_tolerance
        self.estimator_method = estimator_method
        self.refuter_method = refuter_method
        self.confounders_effect_on_t = confounders_effect_on_t
        self.confounders_effect_on_y = confounders_effect_on_y
        self.effect_strength_on_t = effect_strength_on_t
        self.effect_strength_on_y = effect_strength_on_y
        
        if 'logging_level' in kwargs:
            logging.basicConfig(level=kwargs['logging_level'])
        else:
            logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        print(self._error_tolerance)

    def null_refutation_test(self, data=None, dataset="linear", beta=10,
            num_common_causes=1, num_instruments=1, num_samples=100000,
            treatment_is_binary=True):
        # Supports user-provided dataset object
        if data is None:
            data = dowhy.datasets.linear_dataset(beta=beta,
                                             num_common_causes=num_common_causes,
                                             num_instruments=num_instruments,
                                             num_samples=num_samples,
                                             treatment_is_binary=treatment_is_binary)

        model = CausalModel(
            data=data['df'],
            treatment=data["treatment_name"],
            outcome=data["outcome_name"],
            graph=data["gml_graph"],
            proceed_when_unidentifiable=True,
            test_significance=None
        )
        target_estimand = model.identify_effect()
        ate_estimate = model.estimate_effect(
            identified_estimand=target_estimand,
            method_name=self.estimator_method,
            test_significance=None
        )
        true_ate = data["ate"]
        self.logger.debug(true_ate)

        if self.refuter_method == "add_unobserved_common_cause":
        # To test if there are any exceptions
            ref = model.refute_estimate(target_estimand, ate_estimate,
                method_name=self.refuter_method,
                confounders_effect_on_treatment = self.confounders_effect_on_t,
                confounders_effect_on_outcome = self.confounders_effect_on_y,
                effect_strength_on_treatment =self.effect_strength_on_t,
                effect_strength_on_outcome=self.effect_strength_on_y)
            self.logger.debug(ref.new_effect)

            # To test if the estimate is identical if refutation parameters are zero
            refute = model.refute_estimate(target_estimand, ate_estimate,
                method_name=self.refuter_method,
                confounders_effect_on_treatment = self.confounders_effect_on_t,
                confounders_effect_on_outcome = self.confounders_effect_on_y,
                effect_strength_on_treatment = 0,
                effect_strength_on_outcome = 0)
            error = abs(refute.new_effect - ate_estimate.value)
            
            print("Error in refuted estimate = {0} with tolerance {1}%. Estimated={2},After Refutation={3}".format(
                error, self._error_tolerance * 100, ate_estimate.value, refute.new_effect)
            )
            res = True if (error < abs(ate_estimate.value) * self._error_tolerance) else False
            assert res

        elif self.refuter_method == "placebo_treatment_refuter":
            ref = model.refute_estimate(target_estimand, 
                                        ate_estimate,
                                        placebo_treatment_refuter
                                        )
            # This value is hardcoded to be zero as we are runnning this on a linear dataset.
            # Ordinarily, we should expect this value to be zero.
            EXPECTED_PLACEBO_VALUE = 0
            
            error =  abs(ref.new_effect - ate_estimate.value)

            print("Error in the refuted estimate = {0} with tolderence {1}%. Expected Value={2}, After Refutation={3}".format(
                error, self._error_tolerence * 100, EXPECTED_PLACEBO_VALUE, refute.new_effect)
            )

            res = True if (error <  self._error_tolerance)
            assert res 
            

    def binary_treatment_testsuite(self, tests_to_run="all"):
        self.null_refutation_test(num_common_causes=1)
        if tests_to_run != "atleast-one-common-cause":
            self.null_refutation_test(num_common_causes=0)

    def continuous_treatment_testsuite(self, tests_to_run="all"):
        self.null_refutation_test(
                #beta=1,
            num_common_causes=1,
            #num_instruments=2, num_samples=100000,
            treatment_is_binary=False)
        if tests_to_run != "atleast-one-common-cause":
            self.null_refutation_test(num_common_causes=0,
                    treatment_is_binary=False)

