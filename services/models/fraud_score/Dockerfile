# Fraud score model: one image for SageMaker training (`train`) and serving (`serve`).
# Build with `mise run build-model fraud-score`, which tags it with VERSION and
# pushes it to the ECR repository (Floci locally).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/program \
    PATH="/opt/program/bin:${PATH}"

WORKDIR /opt/program

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bin/ bin/
COPY fraud_score_model/ fraud_score_model/
COPY VERSION .

# SageMaker runs training and serving as root inside its own sandbox and needs
# write access to /opt/ml; there is no USER switch here for that reason.
EXPOSE 8080
