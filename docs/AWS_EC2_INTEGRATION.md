# AWS EC2 Integration Guide

## Overview

The Incident Response Automation platform can integrate with AWS EC2 to automatically respond to infrastructure incidents involving EC2 instances. This integration enables automated actions like scaling, stopping/starting instances, modifying instance types, and more.

## Capabilities

### Instance Operations

| Operation | Description | Risk Level | Auto-Execute |
|-----------|-------------|------------|--------------|
| Describe Instances | Get instance details and status | Low | Yes |
| Stop Instance | Gracefully stop an instance | High | Requires Approval |
| Start Instance | Start a stopped instance | Medium | Yes |
| Reboot Instance | Reboot an instance | Medium | Yes |
| Terminate Instance | Permanently delete instance | Critical | No (Always requires approval) |
| Modify Instance Type | Change instance size | High | Requires Approval |
| Create AMI | Take instance snapshot | Low | Yes |

### Auto Scaling Group Operations

| Operation | Description | Risk Level | Auto-Execute |
|-----------|-------------|------------|--------------|
| Set Desired Capacity | Scale ASG up/down | Medium | Yes (with limits) |
| Update Launch Template | Modify ASG configuration | High | Requires Approval |
| Suspend Processes | Pause ASG scaling | Medium | Yes |
| Resume Processes | Resume ASG scaling | Low | Yes |

### Monitoring & Diagnostics

| Operation | Description | Risk Level | Auto-Execute |
|-----------|-------------|------------|--------------|
| Get Instance Metrics | CPU, memory, network from CloudWatch | Low | Yes |
| Get System Logs | Retrieve console output | Low | Yes |
| Describe Instance Status | Health check status | Low | Yes |
| Get Instance Screenshot | Capture console screenshot | Low | Yes |

## Configuration

### 1. AWS Credentials Setup

Update your `.env` file:

```bash
# AWS Configuration
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# Optional: Use IAM Role instead (recommended for production)
# Leave access keys empty and EC2 will use instance role
AWS_USE_IAM_ROLE=true
```

### 2. IAM Policy

Create an IAM policy with appropriate permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EC2ReadOperations",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeTags",
        "ec2:GetConsoleOutput",
        "ec2:GetConsoleScreenshot"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2WriteOperations",
      "Effect": "Allow",
      "Action": [
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances",
        "ec2:ModifyInstanceAttribute",
        "ec2:CreateImage"
      ],
      "Resource": "arn:aws:ec2:*:*:instance/*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/ManagedBy": "incident-response-automation"
        }
      }
    },
    {
      "Sid": "AutoScalingOperations",
      "Effect": "Allow",
      "Action": [
        "autoscaling:DescribeAutoScalingGroups",
        "autoscaling:SetDesiredCapacity",
        "autoscaling:UpdateAutoScalingGroup",
        "autoscaling:SuspendProcesses",
        "autoscaling:ResumeProcesses"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchMetrics",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Enable EC2 Integration

Update `src/config/integrations.yaml`:

```yaml
cloud_providers:
  aws:
    enabled: true
    region: ${AWS_REGION:us-west-2}
    access_key_id: ${AWS_ACCESS_KEY_ID}
    secret_access_key: ${AWS_SECRET_ACCESS_KEY}
    use_iam_role: ${AWS_USE_IAM_ROLE:false}
    
    # Services
    services:
      ec2:
        enabled: true
        
        # Safety limits
        limits:
          max_instances_per_action: 5
          allowed_operations:
            - describe
            - start
            - stop
            - reboot
            - create_image
          
          # Require manual approval for these
          require_approval:
            - terminate
            - modify_instance_type
          
          # Environment protections
          production_protection: true
          protected_tags:
            - Environment: production
            - Critical: true
        
        # Auto Scaling Groups
        auto_scaling:
          enabled: true
          max_scale_up_factor: 2.0  # Can't scale more than 2x current
          min_instances: 2  # Never scale below 2
          max_instances: 50
          cooldown_seconds: 300
        
        # CloudWatch integration
        cloudwatch:
          enabled: true
          metric_period: 300  # 5 minutes
          metrics_to_collect:
            - CPUUtilization
            - NetworkIn
            - NetworkOut
            - StatusCheckFailed
            - DiskReadBytes
            - DiskWriteBytes
```

## Integration Implementation

### EC2 Adapter

Create `src/services/integrations/aws_ec2.py`:

```python
import boto3
from typing import List, Dict, Optional
from .base import BaseIntegration

class EC2Integration(BaseIntegration):
    """AWS EC2 integration adapter"""
    
    def _initialize_client(self):
        """Initialize boto3 EC2 client"""
        session_config = {
            'region_name': self.config.region
        }
        
        if not self.config.use_iam_role:
            session_config.update({
                'aws_access_key_id': self.config.access_key_id,
                'aws_secret_access_key': self.config.secret_access_key
            })
        
        session = boto3.Session(**session_config)
        return {
            'ec2': session.client('ec2'),
            'autoscaling': session.client('autoscaling'),
            'cloudwatch': session.client('cloudwatch')
        }
    
    async def test_connection(self) -> bool:
        """Test AWS EC2 connection"""
        try:
            self.client['ec2'].describe_regions(MaxResults=1)
            return True
        except Exception:
            return False
    
    # ========================================
    # Instance Operations
    # ========================================
    
    async def describe_instances(
        self,
        instance_ids: Optional[List[str]] = None,
        filters: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """Get instance details"""
        
        params = {}
        if instance_ids:
            params['InstanceIds'] = instance_ids
        if filters:
            params['Filters'] = filters
        
        response = self.client['ec2'].describe_instances(**params)
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append({
                    'instance_id': instance['InstanceId'],
                    'instance_type': instance['InstanceType'],
                    'state': instance['State']['Name'],
                    'private_ip': instance.get('PrivateIpAddress'),
                    'public_ip': instance.get('PublicIpAddress'),
                    'launch_time': instance['LaunchTime'],
                    'tags': {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                })
        
        return instances
    
    async def start_instances(
        self,
        instance_ids: List[str]
    ) -> Dict:
        """Start stopped instances"""
        
        return await self.execute_with_circuit_breaker(
            self._start_instances_impl,
            instance_ids=instance_ids
        )
    
    def _start_instances_impl(self, instance_ids: List[str]) -> Dict:
        """Internal start implementation"""
        
        # Validate instance limit
        if len(instance_ids) > self.config.limits.max_instances_per_action:
            raise ValueError(
                f"Cannot start more than {self.config.limits.max_instances_per_action} instances"
            )
        
        response = self.client['ec2'].start_instances(
            InstanceIds=instance_ids
        )
        
        return {
            'success': True,
            'starting_instances': [
                {
                    'instance_id': inst['InstanceId'],
                    'previous_state': inst['PreviousState']['Name'],
                    'current_state': inst['CurrentState']['Name']
                }
                for inst in response['StartingInstances']
            ]
        }
    
    async def stop_instances(
        self,
        instance_ids: List[str],
        force: bool = False
    ) -> Dict:
        """Stop running instances"""
        
        return await self.execute_with_circuit_breaker(
            self._stop_instances_impl,
            instance_ids=instance_ids,
            force=force
        )
    
    def _stop_instances_impl(
        self,
        instance_ids: List[str],
        force: bool = False
    ) -> Dict:
        """Internal stop implementation"""
        
        if len(instance_ids) > self.config.limits.max_instances_per_action:
            raise ValueError(
                f"Cannot stop more than {self.config.limits.max_instances_per_action} instances"
            )
        
        response = self.client['ec2'].stop_instances(
            InstanceIds=instance_ids,
            Force=force
        )
        
        return {
            'success': True,
            'stopping_instances': [
                {
                    'instance_id': inst['InstanceId'],
                    'previous_state': inst['PreviousState']['Name'],
                    'current_state': inst['CurrentState']['Name']
                }
                for inst in response['StoppingInstances']
            ]
        }
    
    async def reboot_instances(
        self,
        instance_ids: List[str]
    ) -> Dict:
        """Reboot instances"""
        
        if len(instance_ids) > self.config.limits.max_instances_per_action:
            raise ValueError(
                f"Cannot reboot more than {self.config.limits.max_instances_per_action} instances"
            )
        
        self.client['ec2'].reboot_instances(InstanceIds=instance_ids)
        
        return {
            'success': True,
            'rebooted_instances': instance_ids
        }
    
    async def create_ami(
        self,
        instance_id: str,
        name: str,
        description: str = ""
    ) -> Dict:
        """Create AMI snapshot of instance"""
        
        response = self.client['ec2'].create_image(
            InstanceId=instance_id,
            Name=name,
            Description=description,
            NoReboot=True  # Don't reboot instance
        )
        
        return {
            'success': True,
            'ami_id': response['ImageId'],
            'instance_id': instance_id
        }
    
    # ========================================
    # Auto Scaling Group Operations
    # ========================================
    
    async def describe_auto_scaling_groups(
        self,
        asg_names: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get ASG details"""
        
        params = {}
        if asg_names:
            params['AutoScalingGroupNames'] = asg_names
        
        response = self.client['autoscaling'].describe_auto_scaling_groups(**params)
        
        return [
            {
                'name': asg['AutoScalingGroupName'],
                'min_size': asg['MinSize'],
                'max_size': asg['MaxSize'],
                'desired_capacity': asg['DesiredCapacity'],
                'current_instances': len(asg['Instances']),
                'healthy_instances': len([
                    i for i in asg['Instances']
                    if i['HealthStatus'] == 'Healthy'
                ]),
                'availability_zones': asg['AvailabilityZones']
            }
            for asg in response['AutoScalingGroups']
        ]
    
    async def set_asg_desired_capacity(
        self,
        asg_name: str,
        desired_capacity: int
    ) -> Dict:
        """Scale Auto Scaling Group"""
        
        # Get current ASG state
        asgs = await self.describe_auto_scaling_groups([asg_name])
        if not asgs:
            raise ValueError(f"ASG {asg_name} not found")
        
        asg = asgs[0]
        current_capacity = asg['desired_capacity']
        
        # Validate scale factor
        if desired_capacity > current_capacity * self.config.auto_scaling.max_scale_up_factor:
            raise ValueError(
                f"Cannot scale more than {self.config.auto_scaling.max_scale_up_factor}x current capacity"
            )
        
        # Validate min/max
        if desired_capacity < self.config.auto_scaling.min_instances:
            raise ValueError(f"Cannot scale below {self.config.auto_scaling.min_instances} instances")
        
        if desired_capacity > self.config.auto_scaling.max_instances:
            raise ValueError(f"Cannot scale above {self.config.auto_scaling.max_instances} instances")
        
        self.client['autoscaling'].set_desired_capacity(
            AutoScalingGroupName=asg_name,
            DesiredCapacity=desired_capacity,
            HonorCooldown=True
        )
        
        return {
            'success': True,
            'asg_name': asg_name,
            'previous_capacity': current_capacity,
            'new_capacity': desired_capacity
        }
    
    # ========================================
    # Monitoring & Diagnostics
    # ========================================
    
    async def get_instance_metrics(
        self,
        instance_id: str,
        metric_name: str,
        period: int = 300,
        statistics: List[str] = ['Average']
    ) -> Dict:
        """Get CloudWatch metrics for instance"""
        
        from datetime import datetime, timedelta
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=30)
        
        response = self.client['cloudwatch'].get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName=metric_name,
            Dimensions=[
                {'Name': 'InstanceId', 'Value': instance_id}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=statistics
        )
        
        datapoints = sorted(
            response['Datapoints'],
            key=lambda x: x['Timestamp']
        )
        
        return {
            'instance_id': instance_id,
            'metric_name': metric_name,
            'datapoints': datapoints,
            'latest_value': datapoints[-1]['Average'] if datapoints else None
        }
    
    async def get_console_output(
        self,
        instance_id: str
    ) -> str:
        """Get instance console output (system logs)"""
        
        response = self.client['ec2'].get_console_output(
            InstanceId=instance_id,
            Latest=True
        )
        
        return response.get('Output', '')
```

## Example Runbooks with EC2

### 1. High CPU - Scale ASG

```yaml
runbooks:
  ec2-high-cpu-scale-asg:
    name: "EC2: Auto-Scale ASG on High CPU"
    description: "Scale EC2 Auto Scaling Group when CPU is high"
    version: "1.0.0"
    enabled: true
    auto_execute: true
    
    trigger_conditions:
      alert_names:
        - EC2HighCPU
        - ASGHighCPU
      severities:
        - critical
        - high
    
    steps:
      - id: get-asg-info
        name: "Get Auto Scaling Group details"
        type: aws_ec2
        params:
          action: describe_auto_scaling_groups
          asg_names:
            - "{{ incident.labels.asg_name }}"
        risk_level: low
        
      - id: calculate-target
        name: "Calculate target capacity"
        type: script_execution
        params:
          language: python
          script: |
            current = step_results['get_asg_info']['output'][0]['desired_capacity']
            target = min(current + 2, 20)  # Add 2, max 20
            return {'target_capacity': target}
        
      - id: scale-asg
        name: "Scale Auto Scaling Group"
        type: aws_ec2
        params:
          action: set_asg_desired_capacity
          asg_name: "{{ incident.labels.asg_name }}"
          desired_capacity: "{{ step_results.calculate_target.output.target_capacity }}"
        risk_level: medium
        
      - id: wait-scaling
        name: "Wait for instances to launch"
        type: wait
        params:
          duration_seconds: 120
        
      - id: verify-cpu
        name: "Verify CPU normalized"
        type: aws_ec2
        params:
          action: get_instance_metrics
          instance_id: "{{ incident.labels.instance_id }}"
          metric_name: CPUUtilization
        
      - id: notify-result
        name: "Notify team"
        type: notification
        params:
          integration: slack
          message: |
            ✅ ASG Scaled Successfully
            
            ASG: {{ incident.labels.asg_name }}
            Previous: {{ step_results.get_asg_info.output[0].desired_capacity }} instances
            New: {{ step_results.calculate_target.output.target_capacity }} instances
            Current CPU: {{ step_results.verify_cpu.output.latest_value }}%
```

### 2. Unhealthy Instance - Replace

```yaml
  ec2-unhealthy-instance-replace:
    name: "EC2: Replace Unhealthy Instance"
    description: "Create AMI and replace unhealthy instance"
    version: "1.0.0"
    enabled: true
    auto_execute: false  # Requires approval
    
    trigger_conditions:
      alert_names:
        - EC2StatusCheckFailed
        - EC2InstanceUnhealthy
    
    steps:
      - id: get-instance-details
        name: "Get instance information"
        type: aws_ec2
        params:
          action: describe_instances
          instance_ids:
            - "{{ incident.labels.instance_id }}"
        
      - id: get-console-logs
        name: "Fetch console logs"
        type: aws_ec2
        params:
          action: get_console_output
          instance_id: "{{ incident.labels.instance_id }}"
        
      - id: ml-analyze-logs
        name: "ML: Analyze logs for failure reason"
        type: ml_analysis
        params:
          task: log_analysis
          logs: "{{ step_results.get_console_logs.output }}"
        
      - id: create-backup-ami
        name: "Create AMI backup"
        type: aws_ec2
        params:
          action: create_ami
          instance_id: "{{ incident.labels.instance_id }}"
          name: "backup-{{ incident.labels.instance_id }}-{{ incident.created_at }}"
          description: "Backup before replacement due to {{ incident.id }}"
        risk_level: low
        
      - id: stop-instance
        name: "Stop unhealthy instance"
        type: aws_ec2
        params:
          action: stop_instances
          instance_ids:
            - "{{ incident.labels.instance_id }}"
        risk_level: high
        requires_approval: true
        
      - id: notify-complete
        name: "Notify team of actions taken"
        type: notification
        params:
          integration: slack
          message: |
            🔧 Unhealthy Instance Handled
            
            Instance: {{ incident.labels.instance_id }}
            Failure Reason: {{ step_results.ml_analyze_logs.output.summary }}
            
            Actions taken:
            ✓ Created backup AMI: {{ step_results.create_backup_ami.output.ami_id }}
            ✓ Stopped instance
            
            ASG will automatically launch replacement.
```

### 3. Disk Space Full

```yaml
  ec2-disk-space-full:
    name: "EC2: Disk Space Full Recovery"
    description: "Handle disk space issues on EC2 instances"
    version: "1.0.0"
    enabled: true
    auto_execute: true
    
    trigger_conditions:
      alert_names:
        - EC2DiskSpaceFull
        - EC2HighDiskUsage
    
    steps:
      - id: get-instance-metrics
        name: "Get disk metrics"
        type: parallel
        steps:
          - id: disk-read
            type: aws_ec2
            params:
              action: get_instance_metrics
              instance_id: "{{ incident.labels.instance_id }}"
              metric_name: DiskReadBytes
              
          - id: disk-write
            type: aws_ec2
            params:
              action: get_instance_metrics
              instance_id: "{{ incident.labels.instance_id }}"
              metric_name: DiskWriteBytes
        
      - id: check-if-in-asg
        name: "Check if instance is in ASG"
        type: aws_ec2
        params:
          action: describe_instances
          instance_ids:
            - "{{ incident.labels.instance_id }}"
        
      - id: conditional-action
        name: "Take appropriate action"
        type: conditional
        condition: "{{ 'aws:autoscaling:groupName' in step_results.check_if_in_asg.output[0].tags }}"
        on_success:
          # In ASG - terminate and let it replace
          - id: terminate-instance
            type: aws_ec2
            params:
              action: stop_instances
              instance_ids:
                - "{{ incident.labels.instance_id }}"
            requires_approval: true
        on_failure:
          # Not in ASG - restart to clear temp files
          - id: reboot-instance
            type: aws_ec2
            params:
              action: reboot_instances
              instance_ids:
                - "{{ incident.labels.instance_id }}"
```

## ML Context Integration

When EC2 alerts fire, the system will automatically enrich the context with:

```python
# In context_builder.py
async def _enrich_ec2_context(
    self,
    alert: PrometheusAlert
) -> Dict:
    """Enrich with EC2 instance information"""
    
    instance_id = alert.labels.get('instance_id')
    if not instance_id:
        return {}
    
    ec2_client = get_integration('aws_ec2')
    
    # Get instance details
    instances = await ec2_client.describe_instances([instance_id])
    
    # Get CloudWatch metrics
    cpu_metrics = await ec2_client.get_instance_metrics(
        instance_id,
        'CPUUtilization'
    )
    
    # Get console logs if instance is failing
    if alert.labels.get('check') == 'StatusCheckFailed':
        console_logs = await ec2_client.get_console_output(instance_id)
    else:
        console_logs = None
    
    return {
        'instance': instances[0] if instances else None,
        'cpu_metrics': cpu_metrics,
        'console_logs': console_logs
    }
```

## Monitoring EC2 Integration

The system will track:

```python
# Prometheus metrics
ec2_operations_total = Counter(
    'ec2_operations_total',
    'Total EC2 operations',
    ['operation', 'status']
)

ec2_operation_duration_seconds = Histogram(
    'ec2_operation_duration_seconds',
    'EC2 operation duration',
    ['operation']
)

ec2_asg_scale_events_total = Counter(
    'ec2_asg_scale_events_total',
    'ASG scaling events',
    ['asg_name', 'direction']
)
```

## Safety Features

### Production Protection

```python
def validate_ec2_operation(
    operation: str,
    instance_ids: List[str],
    config: EC2Config
) -> bool:
    """Validate EC2 operation is safe"""
    
    # Check production protection
    if config.production_protection:
        instances = describe_instances(instance_ids)
        for instance in instances:
            # Check protected tags
            for tag_key, tag_value in config.protected_tags.items():
                if instance['tags'].get(tag_key) == tag_value:
                    if operation in ['terminate', 'stop']:
                        raise ProtectedResourceError(
                            f"Instance {instance['instance_id']} is protected"
                        )
    
    # Check operation is allowed
    if operation not in config.allowed_operations:
        raise UnauthorizedOperationError(f"Operation {operation} not allowed")
    
    # Check instance limit
    if len(instance_ids) > config.max_instances_per_action:
        raise LimitExceededError(
            f"Cannot operate on more than {config.max_instances_per_action} instances"
        )
    
    return True
```

## Testing EC2 Integration

```bash
# Test connection
curl -X POST http://localhost:8000/api/v1/integrations/test \
  -H "Content-Type: application/json" \
  -d '{"integration": "aws_ec2"}'

# Manually trigger EC2 runbook
curl -X POST http://localhost:8000/api/v1/runbooks/ec2-high-cpu-scale-asg/execute \
  -H "Content-Type: application/json" \
  -d '{
    "incident_id": "INC-2026-001",
    "context": {
      "asg_name": "my-app-asg",
      "instance_id": "i-1234567890abcdef0"
    }
  }'
```

## Next Steps

1. **Enable Integration**: Set `enabled: true` in `integrations.yaml`
2. **Configure Credentials**: Add AWS credentials to `.env`
3. **Set Up IAM**: Create IAM policy and attach to user/role
4. **Test Connection**: Run integration test
5. **Create Runbooks**: Adapt example runbooks to your needs
6. **Monitor**: Track EC2 operations in Grafana dashboard

## Conclusion

EC2 integration enables powerful automated responses to infrastructure incidents, from auto-scaling to instance replacement. Combined with ML-powered root cause analysis, the system can intelligently respond to a wide range of EC2-related issues while maintaining strict safety controls.
