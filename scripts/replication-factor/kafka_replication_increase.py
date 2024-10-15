import os
import json
import argparse

"""
Given a set of replicas - current_replicas, and desired replication_factor - rf,
adds needed number of replicas for every patition in a topic.
- keeps current replicas as is (no data movement)
- ensures new replica is not a duplicate
Eg:
current_replicas = [100, 102], desired_rf = 3, num_brokers = 7, new_replicas = [103] so output will be [100, 102, 103]
current_replicas = [100, 106], desired_rf = 3, num_brokers = 7, new_replicas = [101] so output will be [100, 106, 101]
"""
def reassign(args):
    topic_metadata = get_proposal(args.proposal_file)
    print(f"Current topic info: {topic_metadata}")
    reassignment_json = {
        "version": 1,
        "partitions": []
    }
    for partition in topic_metadata['partitions']:
        current_replicas = [replica for replica in partition['replicas']]
        num_replicas = len(current_replicas)
        last_replica = max(current_replicas)
        # kafka replica ids start with 100
        new_replicas = []
        while len(new_replicas) < (args.rf - len(current_replicas)):
            last_replica = 100 + ((last_replica - 100 + 1) % args.num_brokers) # find next replica to assign
            if last_replica in current_replicas: # newly found replica may already be in current set
                continue
            # print(f"State: {len(new_replicas)}, last: {prev}, need: {args.rf - len(current_replicas)}, added: {last_replica}")
            new_replicas.append(last_replica)
        # print(f"Current: {current_replicas}, new: {new_replicas}")
        new_replicas = current_replicas + new_replicas
        reassignment_json["partitions"].append({
            "topic": partition['topic'],
            "partition": partition['partition'],
            "replicas": new_replicas
        })
    with open(args.output, 'w') as f:
        json.dump(reassignment_json, f)
    print("Reassignment JSON file created: reassignment.json")
    print("Contents of reassignment.json:")
    print(json.dumps(reassignment_json, indent=2))

def get_proposal(proposal_file):
    with open(proposal_file, 'r') as file:
        lines = file.readlines()
        reassignment = lines[-1].strip()
    return json.loads(reassignment)



def main():
    parser = argparse.ArgumentParser(description="Process some personal information.")
    parser.add_argument('--num_brokers', type=int, required=True)
    parser.add_argument('--proposal_file', type=str, required=True)
    parser.add_argument('--rf', type=int, required=True)
    parser.add_argument('--output', type=str, default="reassignment.json", required=False)
    args = parser.parse_args()
    reassign(args)

if __name__ == "__main__":
    main()
