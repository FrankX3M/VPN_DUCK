# Add this code to chart_generator.py
# This should be the entire content of the file

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import base64
import datetime
import logging

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

logger = logging.getLogger(__name__)

class ChartGenerator:
    """Generator for server metrics charts"""
    
    @staticmethod
    def generate_metrics_image(metrics_data, chart_type='latency', hours=24):
        """Creates a chart image of metrics
        
        Args:
            metrics_data: Metrics data from API
            chart_type: Chart type (latency, load, resources, packet_loss)
            hours: Number of hours to display
            
        Returns:
            Base64-encoded image string for HTML embedding
        """
        try:
            if not metrics_data or 'history' not in metrics_data or not metrics_data['history']:
                logger.warning("No data for chart generation")
                return None
                
            # Create the figure
            fig, ax = plt.subplots(figsize=(10, 5))
            
            # Convert timestamps to datetime
            # history = metrics_data['history']
            # timestamps = [datetime.datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')) 
            #              if 'timestamp' in item else 
            #              datetime.datetime.fromisoformat(item['hour'].replace('Z', '+00:00')) 
            #              for item in history]
            # In generate_metrics_image method, update the timestamps conversion:
            history = metrics_data['history']
            timestamps = []
            for item in history:
                ts = item.get('timestamp', item.get('hour', ''))
                if isinstance(ts, str):
                    try:
                        # Try to convert strings to datetime objects
                        timestamps.append(datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')))
                    except ValueError:
                        # If conversion fails, use the string as is
                        timestamps.append(ts)
                else:
                    # If it's already a datetime or something else, use it as is
                    timestamps.append(ts)

            # Select data based on chart type
            if chart_type == 'latency':
                # Latency chart
                latency_data = [item.get('avg_latency', 0) for item in history]
                ax.plot(timestamps, latency_data, 'b-', label='Latency (ms)')
                ax.set_ylabel('Latency (ms)')
                ax.set_title('Latency over last 24 hours')
                
            elif chart_type == 'load':
                # Load chart
                load_data = [item.get('load', 0) for item in history]
                ax.plot(timestamps, load_data, 'g-', label='Load (%)')
                ax.set_ylabel('Load (%)')
                ax.set_title('Server Load')
                ax.set_ylim(0, 100)
                
            elif chart_type == 'resources':
                # Resources chart (CPU and memory)
                cpu_data = [item.get('cpu_usage', 0) for item in history]
                memory_data = [item.get('memory_usage', 0) for item in history]
                
                ax.plot(timestamps, cpu_data, 'r-', label='CPU (%)')
                ax.plot(timestamps, memory_data, 'b-', label='Memory (%)')
                ax.set_ylabel('Usage (%)')
                ax.set_title('Resource Usage')
                ax.set_ylim(0, 100)
                ax.legend()
                
            elif chart_type == 'packet_loss':
                # Packet loss chart
                packet_loss_data = [item.get('avg_packet_loss', 0) for item in history]
                ax.plot(timestamps, packet_loss_data, 'r-', label='Packet Loss (%)')
                ax.set_ylabel('Packet Loss (%)')
                ax.set_title('Packet Loss')
                ax.set_ylim(0, 100)
            
            # Format X axis for date display
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%d.%m'))
            plt.xticks(rotation=0)
            
            # Add grid and legend
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend()
            
            # Save chart to memory
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            
            # Encode as base64 for HTML embedding
            image_png = buffer.getvalue()
            buffer.close()
            plt.close(fig)  # Close figure to free memory
            
            encoded = base64.b64encode(image_png).decode('utf-8')
            return encoded
        
        except Exception as e:
            logger.exception(f"Error generating chart: {str(e)}")
            return None
            
    @staticmethod
    def generate_plotly_chart(metrics_data, chart_type='dashboard'):
        """Creates an interactive Plotly chart
        
        Args:
            metrics_data: Metrics data from API
            chart_type: Chart type (dashboard, server_detail)
            
        Returns:
            HTML code for template embedding
        """
        if not PLOTLY_AVAILABLE:
            logger.warning("Plotly not available, skipping interactive chart generation")
            return None
            
        try:
            if not metrics_data or 'history' not in metrics_data or not metrics_data['history']:
                return None
                
            # Create figure with subplots
            fig = make_subplots(rows=2, cols=1, 
                               subplot_titles=("Latency and Packet Loss", "Resource Usage"),
                               shared_xaxes=True,
                               vertical_spacing=0.1)
            
            # Convert timestamps
            history = metrics_data['history']
            timestamps = [item.get('timestamp', item.get('hour', '')) for item in history]
            
            # Add traces to chart
            fig.add_trace(
                go.Scatter(x=timestamps, y=[item.get('avg_latency', 0) for item in history],
                          mode='lines+markers', name='Latency (ms)'),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=timestamps, y=[item.get('avg_packet_loss', 0) for item in history],
                          mode='lines+markers', name='Packet Loss (%)'),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=timestamps, y=[item.get('cpu_usage', 0) for item in history],
                          mode='lines+markers', name='CPU (%)'),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Scatter(x=timestamps, y=[item.get('memory_usage', 0) for item in history],
                          mode='lines+markers', name='Memory (%)'),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                height=700,
                title_text="Server Metrics",
                hovermode="x unified"
            )
            
            # Set Y axis ranges
            fig.update_yaxes(title_text="Latency (ms) / Loss (%)", row=1, col=1)
            fig.update_yaxes(title_text="Usage (%)", range=[0, 100], row=2, col=1)
            
            # Return HTML for template embedding
            return fig.to_html(full_html=False, include_plotlyjs='cdn')
            
        except Exception as e:
            logger.exception(f"Error generating interactive chart: {str(e)}")
            return None