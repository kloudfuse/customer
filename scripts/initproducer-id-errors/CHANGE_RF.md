1. Copy topics.json into kafka broker pod
   - kubectl cp topics.json kafka-broker-0:/tmp/topics.json
2. Get reassignment json from kafka
  - kubectl exec -it kafka-broker-0 bash
  - unset JMX_PORT
  - cd /opt/bitnami/kafka/bin/
  - ./kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --topics-to-move-json-file /tmp/topics.json --broker-list <broker_list> --generate > /tmp/proposal.json
  - Here <broker_list> should be 100,101...100+num_brokers-1. Eg: if there are 7 brokers then pass 100,101,102,103,104,105,106
3. Copy proposal.json out of kafka broker pod
   - kubectl cp kafka-broker-0:/tmp/proposal.json /tmp/proposal.json
4. Run script to create new assignment plan
   - python3 kafka_replication_increase.py --output /tmp/reassignment.json --num_brokers <number_of_kafka_brokers> --rf <desired_rf> --proposal_file /tmp/proposal.json
   - above script will produce reassignment file /tmp/reassignment.json
5. Copy new assignment plan into kafka broker pod
   - kubectl cp /tmp/reassignment.json kafka-broker-0:/tmp/reassignment.json
6. Execute new assignment plan
  - kubectl exec -it kafka-broker-0 bash
  - unset JMX_PORT
  - cd /opt/bitnami/kafka/bin/
  - ./kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --reassignment-json-file /tmp/reassignment.json --execute
  - Once above command is run, there should be a message that looks like this
  ```
  - Save this to use as the --reassignment-json-file option during rollback
Successfully started partition reassignments for __transaction_state-0,__transaction_state-1,__transaction_state-2,__transaction_state-3,__transaction_state-4,__transaction_state-5,__transaction_state-6,__transaction_state-7,__transaction_state-8,__transaction_state-9,__transaction_state-10,__transaction_state-11,__transaction_state-12,__transaction_state-13,__transaction_state-14,__transaction_state-15,__transaction_state-16,__transaction_state-17,__transaction_state-18,__transaction_state-19,__transaction_state-20,__transaction_state-21,__transaction_state-22,__transaction_state-23,__transaction_state-24,__transaction_state-25,__transaction_state-26,__transaction_state-27,__transaction_state-28,__transaction_state-29,__transaction_state-30,__transaction_state-31,__transaction_state-32,__transaction_state-33,__transaction_state-34,__transaction_state-35,__transaction_state-36,__transaction_state-37,__transaction_state-38,__transaction_state-39,__transaction_state-40,__transaction_state-41,__transaction_state-42,__transaction_state-43,__transaction_state-44,__transaction_state-45,__transaction_state-46,__transaction_state-47,__transaction_state-48,__transaction_state-49

  ```
  - ./kafka-reassign-partitions.sh --bootstrap-server localhost:9092 --reassignment-json-file /tmp/reassignment.json --verify
  - Output of this command would look like this.
  ```
Status of partition reassignment:
Reassignment of partition __transaction_state-0 is completed.
Reassignment of partition __transaction_state-1 is completed.
Reassignment of partition __transaction_state-2 is completed.
Reassignment of partition __transaction_state-3 is completed.
Reassignment of partition __transaction_state-4 is completed.
Reassignment of partition __transaction_state-5 is completed.
Reassignment of partition __transaction_state-6 is completed.
Reassignment of partition __transaction_state-7 is completed.
Reassignment of partition __transaction_state-8 is completed.
Reassignment of partition __transaction_state-9 is completed.
Reassignment of partition __transaction_state-10 is completed.
Reassignment of partition __transaction_state-11 is completed.
Reassignment of partition __transaction_state-12 is completed.
Reassignment of partition __transaction_state-13 is completed.
Reassignment of partition __transaction_state-14 is completed.
Reassignment of partition __transaction_state-15 is completed.
Reassignment of partition __transaction_state-16 is completed.
Reassignment of partition __transaction_state-17 is completed.
Reassignment of partition __transaction_state-18 is completed.
Reassignment of partition __transaction_state-19 is completed.
Reassignment of partition __transaction_state-20 is completed.
Reassignment of partition __transaction_state-21 is completed.
Reassignment of partition __transaction_state-22 is completed.
Reassignment of partition __transaction_state-23 is completed.
Reassignment of partition __transaction_state-24 is completed.
Reassignment of partition __transaction_state-25 is completed.
Reassignment of partition __transaction_state-26 is completed.
Reassignment of partition __transaction_state-27 is completed.
Reassignment of partition __transaction_state-28 is completed.
Reassignment of partition __transaction_state-29 is completed.
Reassignment of partition __transaction_state-30 is completed.
Reassignment of partition __transaction_state-31 is completed.
Reassignment of partition __transaction_state-32 is completed.
Reassignment of partition __transaction_state-33 is completed.
Reassignment of partition __transaction_state-34 is completed.
Reassignment of partition __transaction_state-35 is completed.
Reassignment of partition __transaction_state-36 is completed.
Reassignment of partition __transaction_state-37 is completed.
Reassignment of partition __transaction_state-38 is completed.
Reassignment of partition __transaction_state-39 is completed.
Reassignment of partition __transaction_state-40 is completed.
Reassignment of partition __transaction_state-41 is completed.
Reassignment of partition __transaction_state-42 is completed.
Reassignment of partition __transaction_state-43 is completed.
Reassignment of partition __transaction_state-44 is completed.
Reassignment of partition __transaction_state-45 is completed.
Reassignment of partition __transaction_state-46 is completed.
Reassignment of partition __transaction_state-47 is completed.
Reassignment of partition __transaction_state-48 is completed.
Reassignment of partition __transaction_state-49 is completed.
  ```
8.  Set min.insync.replicas to 2
  - kafka-configs.sh --bootstrap-server localhost:9092 --alter --entity-type topics --entity-name __transaction_state  --add-config min.insync.replicas=2

