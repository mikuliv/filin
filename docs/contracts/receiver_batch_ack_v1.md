# receiver_batch_ack_v1

ACK связывает batch/attempt с durable receiver commit и содержит ровно один результат на событие. Неизвестный статус, partial ACK, неверный hash или `durable=false` отклоняются connector.
