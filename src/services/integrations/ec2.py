from __future__ import annotations

from typing import Any, Dict, List

from src.services.integrations.base import BaseIntegration


class EC2Integration(BaseIntegration):
    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for EC2 integration") from exc
        return boto3.client("ec2", region_name=self.config.get("region"))

    def _asg_client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for EC2 integration") from exc
        return boto3.client("autoscaling", region_name=self.config.get("region"))

    def _cloudwatch(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for EC2 integration") from exc
        return boto3.client("cloudwatch", region_name=self.config.get("region"))

    async def describe_instances(self, instance_ids: List[str]) -> Dict[str, Any]:
        client = self._client()
        return client.describe_instances(InstanceIds=instance_ids)

    async def start_instances(self, instance_ids: List[str]) -> Dict[str, Any]:
        client = self._client()
        return client.start_instances(InstanceIds=instance_ids)

    async def stop_instances(self, instance_ids: List[str]) -> Dict[str, Any]:
        client = self._client()
        return client.stop_instances(InstanceIds=instance_ids)

    async def set_asg_desired_capacity(self, asg_name: str, desired_capacity: int) -> Dict[str, Any]:
        client = self._asg_client()
        return client.set_desired_capacity(AutoScalingGroupName=asg_name, DesiredCapacity=desired_capacity)

    async def get_instance_metrics(self, instance_id: str, metric_name: str) -> Dict[str, Any]:
        client = self._cloudwatch()
        return client.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName=metric_name,
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=self.config.get("metrics_start_time"),
            EndTime=self.config.get("metrics_end_time"),
            Period=self.config.get("metrics_period_seconds", 300),
            Statistics=["Average"],
        )
