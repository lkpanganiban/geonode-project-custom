# -*- coding: utf-8 -*-
"""
Sample Celery tasks for testing the monitoring system
"""
from celery import shared_task, current_task
import time
import random


@shared_task(
    name='geonode_project.monitoring.sample_task',
    bind=True,
    queue='default',  # Use 'default' queue to match worker configuration
    ignore_result=False,
    store_eager_result=True
)
def sample_task(self, duration=5, should_succeed=True):
    """
    A sample task for testing the monitoring system.
    
    Args:
        duration: How long the task should run (in seconds)
        should_succeed: If False, the task will randomly fail
    
    Returns:
        dict: Task result with execution details
    """
    print(f"Sample task started with duration={duration}s, should_succeed={should_succeed}")
    
    try:
        # Simulate work
        for i in range(int(duration)):
            time.sleep(1)
            print(f"Sample task progress: {i+1}/{duration}")
            # Update task state with progress
            self.update_state(
                state='PROGRESS',
                meta={'current': i+1, 'total': duration, 'percent': int((i+1)/duration*100)}
            )
        
        # Randomly fail if should_succeed is False
        if not should_succeed and random.choice([True, False]):
            raise Exception("Task failed randomly (as requested)")
        
        result = {
            'task_name': 'sample_task',
            'duration': duration,
            'status': 'completed',
            'message': f'Task completed successfully after {duration} seconds'
        }
        
        print(f"Sample task completed: {result}")
        return result
        
    except Exception as e:
        print(f"Sample task failed: {e}")
        raise


@shared_task(
    name='geonode_project.monitoring.hello_world',
    bind=True,
    queue='default',  # Use 'default' queue to match worker configuration
    ignore_result=False,
    store_eager_result=True
)
def hello_world(self, name="World"):
    """
    A simple hello world task for testing.
    
    Args:
        name: Name to greet
    
    Returns:
        str: Greeting message
    """
    message = f"Hello, {name}!"
    print(message)
    return message


@shared_task(
    name='geonode_project.monitoring.calculate_sum',
    bind=True,
    queue='default',  # Use 'default' queue to match worker configuration
    ignore_result=False,
    store_eager_result=True
)
def calculate_sum(self, numbers):
    """
    Calculate sum of a list of numbers.
    
    Args:
        numbers: List of numbers to sum
    
    Returns:
        dict: Result with sum and count
    """
    print(f"Calculating sum of: {numbers}")
    result = sum(numbers)
    return {
        'numbers': numbers,
        'sum': result,
        'count': len(numbers)
    }
