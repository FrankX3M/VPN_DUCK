import io
import base64
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import plotly
import json
import logging

logger = logging.getLogger(__name__)

class ChartGenerator:
    """
    Utility class for generating charts and visualizations
    for server metrics using matplotlib and plotly.
    """
    
    @staticmethod
    def generate_metrics_image(metrics, metric_type, hours=24):
        """
        Generate a base64 encoded image chart for a specific metric type.
        
        Args:
            metrics (dict): Dictionary containing metrics data
            metric_type (str): Type of metric to visualize ('latency', 'load', 'resources', 'packet_loss')
            hours (int): Number of hours to include in the chart
        
        Returns:
            str: Base64 encoded image
        """
        try:
            if not metrics or 'history' not in metrics or not metrics['history']:
                logger.warning(f"No metrics data available for {metric_type}")
                return None
            
            plt.figure(figsize=(10, 5))
            
            # Sort data points by timestamp
            history = sorted(metrics['history'], key=lambda x: x.get('timestamp', 0))
            
            # Filter data for the requested time period and get the metric values
            timestamps = []
            values = []
            
            for entry in history:
                if metric_type == 'latency':
                    value = entry.get('latency_ms')
                elif metric_type == 'load':
                    value = entry.get('server_load')
                elif metric_type == 'resources':
                    value = entry.get('resource_usage_percent')
                elif metric_type == 'packet_loss':
                    value = entry.get('packet_loss_percent')
                else:
                    value = None
                
                if value is not None:
                    timestamps.append(entry.get('timestamp'))
                    values.append(value)
            
            if not timestamps or not values:
                logger.warning(f"No valid data points for {metric_type}")
                return None
            
            # Create the plot
            plt.plot(timestamps, values, 'b-', linewidth=2)
            plt.grid(True, alpha=0.3)
            
            # Set chart title and labels
            if metric_type == 'latency':
                plt.title(f'Latency (Last {hours} Hours)')
                plt.ylabel('Latency (ms)')
            elif metric_type == 'load':
                plt.title(f'Server Load (Last {hours} Hours)')
                plt.ylabel('Load')
            elif metric_type == 'resources':
                plt.title(f'Resource Usage (Last {hours} Hours)')
                plt.ylabel('Usage (%)')
            elif metric_type == 'packet_loss':
                plt.title(f'Packet Loss (Last {hours} Hours)')
                plt.ylabel('Loss (%)')
            
            plt.xlabel('Time')
            
            # Format the chart
            plt.tight_layout()
            
            # Save the plot to a bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            
            # Encode as base64
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            plt.close()
            
            return img_str
            
        except Exception as e:
            logger.exception(f"Error generating {metric_type} chart: {str(e)}")
            return None
    
    @staticmethod
    def generate_plotly_chart(metrics, chart_type):
        """
        Generate an interactive Plotly chart for metrics visualization.
        
        Args:
            metrics (dict): Dictionary containing metrics data
            chart_type (str): Type of chart to generate ('server_detail', 'dashboard')
        
        Returns:
            str: HTML component with the interactive chart
        """
        try:
            if not metrics or 'history' not in metrics or not metrics['history']:
                logger.warning(f"No metrics data available for {chart_type}")
                return None
            
            history = sorted(metrics['history'], key=lambda x: x.get('timestamp', 0))
            
            timestamps = [entry.get('timestamp') for entry in history if entry.get('timestamp')]
            latency = [entry.get('latency_ms') for entry in history if entry.get('latency_ms') is not None]
            packet_loss = [entry.get('packet_loss_percent') for entry in history if entry.get('packet_loss_percent') is not None]
            
            if not timestamps or (not latency and not packet_loss):
                logger.warning(f"Insufficient data points for {chart_type} chart")
                return None
            
            fig = go.Figure()
            
            # Add traces
            if latency:
                fig.add_trace(go.Scatter(
                    x=timestamps, 
                    y=latency,
                    mode='lines',
                    name='Latency (ms)'
                ))
            
            if packet_loss:
                fig.add_trace(go.Scatter(
                    x=timestamps, 
                    y=packet_loss,
                    mode='lines',
                    name='Packet Loss (%)',
                    yaxis='y2'
                ))
            
            # Update layout
            fig.update_layout(
                title='Server Performance Metrics',
                xaxis_title='Time',
                yaxis=dict(
                    title='Latency (ms)',
                    titlefont=dict(color="#1f77b4"),
                    tickfont=dict(color="#1f77b4")
                ),
                yaxis2=dict(
                    title='Packet Loss (%)',
                    titlefont=dict(color="#ff7f0e"),
                    tickfont=dict(color="#ff7f0e"),
                    anchor="x",
                    overlaying="y",
                    side="right"
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                hovermode='x unified'
            )
            
            # Create the HTML
            chart_html = plotly.offline.plot(
                fig, 
                include_plotlyjs=True, 
                output_type='div'
            )
            
            return chart_html
            
        except Exception as e:
            logger.exception(f"Error generating interactive chart: {str(e)}")
            return None