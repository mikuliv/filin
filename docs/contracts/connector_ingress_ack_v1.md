# connector_ingress_ack_v1

ACK содержит linkage к request, connector instance и durable journal commit, а также accepted/duplicate/rejected множества. `durable=true` выдаётся только после успешного journal commit.
