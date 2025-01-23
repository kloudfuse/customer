Symptom:
Logs parser will stop consuming from partitions with errors like this:
21:18:54.370 [logs-parser-akka.actor.default-dispatcher-5] WARN akka.stream.scaladsl.RestartWithBackoffSource ---> Restarting stream due to failure [1]: org.apache.kafka.common.errors.TimeoutException: Timeout expired after 60000 milliseconds while awaiting InitProducerId

Cause:
- Failure to start a transaction on Kafka.
- This process internally uses a topic named "__transaction_state" in kafka.
- For fault tolerance, this topic should have more than one replica. If this topic's rf is set to 1, above error can happen.

Fix:
1) Add this under kafka section in kfuse values.yaml
```
extraConfigYaml:
  transaction.state.log.replication.factor: 3
  transaction.state.log.min.isr: 2
```
2) Run replication factor increase script for __transaction_state topic
3) Find and cleanup hung transactions
   - kubectl exec -it kafka-broker-0 bash
   - unset JMX_PORT
   - cd /opt/bitnami/kafka/bin/
   - ./kafka-transactions.sh --bootstrap-server :9092 list | grep PrepareAbort
   - restart all brokers that appear as coordinator for these transactions.
     - Note: Broker id starts with 100, typically broker id 100 will be pod 0 and so on.

