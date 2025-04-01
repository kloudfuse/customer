# Scale Up Kloudfuse

To handle increased volume of data, kloudfuse stack can be scaled up by updating the node instance type of the node pool to higher level. This runbook describes how to add additional capacity for running kloudfuse stack through change in the instance type.

## When to scale Up
Sudden increase in the incoming volume of logs, metrics, traces, RUM, etc. will impact the kloudfuse stack in the following way:
### User Visible Impact
* Lagging of data as seen from the UI - older data is visible; more recent data is not visible
* Alert rule status seen as “No Data”
* UI showing various query failure error messages
### Internal Impact
* Increased CPU, memory and disk consumption used by the kloudfuse services and pods
* Crashing of various kloudfuse pods (ingester, kafka, etc.)
* Increased consumer lag in logs, metrics, APM kafka topics.
If the incoming volume increase is temporary, the user visible impact will be temporary and kloudfuse cluster will recover on its own.
If the incoming volume increase is longer term (or permanent), kloudfuse cluster will need to be scaled.

Executing this runbook requires additional investigation; therefore, this runbook should not be executed without involvement of the kloudfuse support.

To update the instance type (with higher resources) follow the steps below:
### Preparation
- [ ] Review and validate if the existing customer values yaml file is correctly configured and up-to-date wrt actual kloudfuse installation. This is important if are changes made directly on the kloudfuse cluster that are not reflected in the customer values yaml. For example, if PVC is resized on the kloudfuse cluster, values yaml file might not have been updated.
- [ ] Adjust the customer values yaml file by:
    * increasing number of partitions for each streams (logs, metrics, etc. based on increased volume) by the right amount.
        * logs - increase the partitions of the logs_ingest and kf_logs topics
        * traces - increase the partitions of the kf_traces, kf_traces_errors and kf_traces_metrics
        * metrics - increase the partitions of the kf_metrics and kf_metrics_rollup
        * for some services such as, logs-parser, etc. number of replicas should be increased as well.
    * Get the customer value yaml file reviewed by the CS as well as engineering team. This file can be kept ready and reviewed in anticipation of expected volume increase.
### Execution      
- [ ] Increase the capacity of the AWS or GCP node pool by changing the instance type (or creating a new node pool with higher instance type and deleting old node pool). The kloudfuse installation requires all nodes to be of the same type and using the same set of taints and labels.
- [ ] Once the kubernetes nodes are replaced and the new nodes are ready to run pods, do the helm upgrade using the updated customer values yaml using the same version as currently installed. This is to avoid accidentally doing software upgrade in addition to scaling the kloudfuse cluster.
- [ ] Verify that all pods and services are up and running and evenly distributed among the old and the new nodes. You can use the control plane’s overview page to confirm that kloudfuse stack is running fine.


## Validation
1. Monitor the kloudfuse control plane to ensure that kloudfuse stack is running fine - all pods and services should be up and running, pinot segment status should all be GOOD, etc.
2. It might take some time for kafka consumer lags for various topics to be reduced to its normal as the new capacity has to deal with data queued in kafka as well as new incoming data. The consumer lags for various topics should be monitored at the individual topic and partition level to ensure that all partitions are consuming properly.
3. Checkin the customer value yaml file in the appropriate customer git repo.
4. Verify that the control plane alerts are no longer firing
5. Control plane overview status is all GREEN
6. Individual stream specific control plane dashboards are all GREEN
7. Kloudfuse UI does not show any lag and recent data is visible
8. Verify that alert rules configured by the customer on the kloudfuse cluster are in “Healthy” state.
