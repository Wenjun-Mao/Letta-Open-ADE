FROM python:3.12.12-slim-bookworm@sha256:228390eced221ad2986a3dd77e10b1accca6ba8ceb36f1572de1b346a337cc1a
ARG PROBE_CANCELLATION_TOKEN
COPY cancellation_probe.py /probe-cancellation.py
RUN python3 -u /probe-cancellation.py ADE_PROBE_BUILDKIT_SENTINEL "${PROBE_CANCELLATION_TOKEN}"
