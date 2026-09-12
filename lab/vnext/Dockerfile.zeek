FROM zeek/zeek:latest
ARG SOURCE_COMMIT=unknown
ARG BUILD_TIMESTAMP=unknown
ARG DOCKERFILE_SHA256=unknown
ARG BUILD_CONTEXT_SHA256=unknown
LABEL org.opencontainers.image.title="Filin vNext Zeek processor" \
      org.opencontainers.image.revision=$SOURCE_COMMIT \
      org.opencontainers.image.created=$BUILD_TIMESTAMP \
      dev.filin.dockerfile.sha256=$DOCKERFILE_SHA256 \
      dev.filin.context.sha256=$BUILD_CONTEXT_SHA256 \
      dev.filin.classification="engineering-only"
ENTRYPOINT []
CMD ["sleep", "86400"]
