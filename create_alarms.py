#!/usr/bin/env python3

import boto3

rebooted_instances = set({})

def is_instance_in_reboot_list(instance_name):
    return instance_name in rebooted_instances

def check_response(response):
    if not(response is None):
        status_code = response["ResponseMetadata"]["HTTPStatusCode"]
        if status_code == 200:
            return True
        else:
            return False

def get_instance_ids_names(ec2_client):

    instance_ids_names = []
    if not(ec2_client is None):
        response = ec2_client.describe_instances()
        if(check_response(response)):
            for reservation in response.get('Reservations',[{}]):
                for instance in reservation.get("Instances",{}):
                    instance_ids_names.append((instance.get("InstanceId",None),instance.get("KeyName",None)))

    return instance_ids_names


def get_instance_alarm_metrics(cloudwatch_client):

    instance_metrics = {}
    if not(cloudwatch_client is None):
        response = cloudwatch_client.describe_alarms()
        if (check_response(response)):
            metric_alarms = response.get("MetricAlarms",[])
            for i in range(len(metric_alarms)):

                for dimension in metric_alarms[i]["Dimensions"]:
                    if dimension["Name"] == "InstanceId":
                        instance_id = dimension["Value"]
                if not(instance_id is None):
                    metric_name = metric_alarms[i]["MetricName"]
                    metrics = instance_metrics.get(instance_id,set())
                    metrics.add(metric_name)
                    instance_metrics[instance_id] = metrics
    return instance_metrics


def set_cpuutilization_alarm(cloudwatch_client,instance_id,instance_name):
    if not(cloudwatch_client is None):
        try:
            response = cloudwatch_client.put_metric_alarm(
                AlarmName = instance_name + ' CPU Monitor',
                AlarmDescription='Created through boto3 API',
                MetricName='CPUUtilization',
                ComparisonOperator='GreaterThanOrEqualToThreshold',
                Threshold=90,
                Namespace='AWS/EC2',
                ActionsEnabled=True,
                AlarmActions = ['arn:aws:sns:<<region_name>>:<<account_id>>:<<topic_name>>'],
                Period= 300,
                EvaluationPeriods=10,
                Statistic='Average',
                Dimensions=[
                    {
                        'Name': 'InstanceId',
                        'Value': instance_id
                    }
                ],
                DatapointsToAlarm = 10,
                TreatMissingData = 'missing',
                Unit = "Percent"
                )
            if check_response(response):
                print("CPUUtilization Alarm set for instance:\t",instance_name)
                return
        except botocore.exceptions.ClientError:
            print("put_metric_alarm: invalid arg")
    print("unable to set CPUUtilization Alarm for instance:\t",instance_name)


def set_statuscheck_alarm(cloudwatch_client,instance_id,instance_name):
    if not(cloudwatch_client is None):
        try:
            response = cloudwatch_client.put_metric_alarm(
                AlarmName = instance_name + ' Status Monitor',
                AlarmDescription='Created through boto3 API',
                MetricName='StatusCheckFailed',
                ComparisonOperator='GreaterThanOrEqualToThreshold',
                Threshold=1,
                Namespace='AWS/EC2',
                ActionsEnabled=True,
                AlarmActions = ['arn:aws:sns:<<region_name>>:<<account_id>>:<<topic_name>>'],
                Period= 60,
                EvaluationPeriods=10,
                Statistic='Maximum',
                Dimensions=[
                    {
                        'Name': 'InstanceId',
                        'Value': instance_id
                    }
                ],
                DatapointsToAlarm = 10,
                TreatMissingData = 'missing',
                Unit = "Count"
                )
            if check_response(response):
                print("StatusCheck Alarm set for instance:\t",instance_name)
                return
        except botocore.exceptions.ClientError:
            print("put_metric_alarm: invalid arg")
    print("unable to set StatusCheck Alarm for instance:\t",instance_name)

def setAlarms(instance_ids_names,instance_alarm_metrics):
    for instance_id,instance_name in instance_ids_names:
        if(is_instance_in_reboot_list(instance_name)):
            ### if there are no alarms set on this instance
            if not (instance_id in instance_alarm_metrics):
                set_cpuutilization_alarm(cloudwatch_client,instance_id,instance_name)
                set_statuscheck_alarm(cloudwatch_client,instance_id,instance_name)
            else:
                metrics_for_instance = instance_alarm_metrics[instance_id]
                ### if instance has only CPUUtilization Monitor set
                if not ("CPUUtilization" in metrics_for_instance):
                    set_cpuutilization_alarm(cloudwatch_client,instance_id,instance_name)
                ### if instance has only StatusCheckFailed Monitor set
                if not ("StatusCheckFailed" in metrics_for_instance):
                    set_statuscheck_alarm(cloudwatch_client,instance_id,instance_name)
        else:
            continue



if __name__ == "__main__":

    print("start...")

    ### creating ec2 client
    #if configured in AWS CLI or configuration file
    ec2_client = boto3.client('ec2')
    #if no AWS configuration file exists
    #ec2_client = boto3.client('ec2',
        #aws_access_key_id='<<access_key_id>>',
        #aws_secret_access_key='<<secret_access_key>>',
        #region_name='<<region_name>>')

    # retrieve instance ids and names
    instance_ids_names = get_instance_ids_names(ec2_client)

    ### creating cloudwatch client
    #if configured in AWS CLI or configuration file
    cloudwatch_client = boto3.client('cloudwatch')
    #cloudwatch_client = boto3.client('cloudwatch',
        #aws_access_key_id='<<access_key_id>>',
        #aws_secret_access_key='<<secret_access_key>>',
        #region_name='<<region_name>>')


    instance_alarm_metrics = get_instance_alarm_metrics(cloudwatch_client)

    setAlarms(instance_ids_names,instance_alarm_metrics)

    print("end")
