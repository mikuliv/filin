FROM python@sha256:e031123e3d85762b141ad1cbc56452ba69c6e722ebf2f042cc0dc86c47c0d8b3
WORKDIR /opt/filin
COPY staging /opt/filin/staging
COPY rehearsal /opt/filin/rehearsal
RUN mkdir -p /var/lib/filin && chown -R 65532:65532 /opt/filin /var/lib/filin
USER 65532:65532
ENV PYTHONPATH=/opt/filin PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m"]
