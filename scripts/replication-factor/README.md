1. Copy topics.json into kafka broker pod
   - kubectl cp topics.json kafka-broker-0:/tmp/topics.json
2. Get reassignment json from kafka
  - kubectl exec -it kafka-broker-0 bash
  - unset JMX_PORT
  - cd /opt/bitnami/kafka/bin/
  - ./kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --topics-to-move-json-file /tmp/topics.json --broker-list 100,101,102,103,104,105,106 --generate > /tmp/proposal.json
3. Copy proposal.json out of kafka broker pod
   - kubectl cp kafka-broker-0:/tmp/proposal.json /tmp/proposal.json
4. Run script to create new assignment plan
   - python3 kafka_replication_increase.py --output /tmp/reassignment.json --num_brokers 7 --proposal_file /tmp/proposal.json 
5. Copy new assignment plan into kafka broker pod
   - kubectl cp /tmp/reassignment.json kafka-broker-0:/tmp/reassignment.json
6. Execute new assignment plan
  - kubectl exec -it kafka-broker-0 bash
  - unset JMX_PORT
  - cd /opt/bitnami/kafka/bin/
  - ./kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --reassignment-json-file /tmp/reassignment.json --execute
  - ./kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --reassignment-json-file /tmp/reassignment.json --verify
