# Model card: fraud-score

Stand-in for a SageMaker Model Card, which Floci does not emulate. Keep it next
to the code it describes and update it with every change that alters behaviour.

## Purpose

Scores each payment for fraud risk, in real time, beside the payment (never in
front of it). The score and its reason codes feed the decision statement
(approve, review, block) in week 4. It is not used for credit or any other
customer-facing decision.

## Model

| | |
| --- | --- |
| Algorithm | XGBoost gradient-boosted trees, `binary:logistic` |
| Inputs | `feature_spec.json` (feature version `v1`): amount, payment counts (1 h, 24 h), distinct provinces (24 h), 30-day mean amount and ratio, new beneficiary, SIM swap (72 h), new device, night (SAST), channel |
| Output | Probability of fraud in [0, 1], plus the top three inputs that raised it (SHAP contributions) |
| Not used | Name, ID number, address, age, gender, race or any proxy for them. Province is used only as a count of distinct provinces, not as a value |
| Image | `weaver/fraud-score:<VERSION>`, Python 3.12, xgboost-cpu |

## Data

POC: synthetic only. `dataset.py` generates normal ZAR traffic for a seeded
population and injects labelled scenarios: account takeover (with and without
SIM swap), authorised push payment scams, card testing and single
card-not-present fraud, plus benign look-alikes (phone upgrades, new payees,
bursts of small purchases, travel). Features come from the reference
implementation that the Flink statement is tested against. Rows are split by
time: train 70%, validation 15%, test 15%.

Synthetic data proves the pipeline, not the model. Before any real use the
model must be retrained on labelled production data (confirmed fraud and
charge-backs), with POPIA sign-off on cross-border processing.

## Evaluation

Registered per version in MLflow: AUC-PR and AUC-ROC on validation and test,
and recall at 90% and 50% precision with the thresholds that give them. The
quality gate for release is test AUC-PR of at least 0.70. Single
card-not-present fraud is deliberately close to normal spend, so recall below
1.0 is expected.

## Limitations and risks

- Synthetic behaviour is simpler than real behaviour; scores will not be calibrated on real data.
- New customers have short histories, so 30-day features are noisy for them.
- Fraud patterns drift. Week 5 adds a drift check over `txn-features` and `fraud-scores`; in AWS, Model Monitor on captured data.
- Reason codes explain the model, not the fraud: they are for analysts, not for customers.

## Ownership and release

Released only through `pipeline approve`, which requires the quality gate and
records the release time in MLflow. In npr and prod the release is a pull request
that changes `models.auto.tfvars.json`.
