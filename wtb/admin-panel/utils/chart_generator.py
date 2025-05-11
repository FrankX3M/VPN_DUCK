import os
import logging
import base64
from io import BytesIO
from datetime import datetime

logger = logging.getLogger(__name__)

class ChartGenerator:
    """Utility class for generating charts and visualizations."""
    
    def __init__(self):
        """Initialize chart generator."""
        self.chart_directory = os.path.join('static', 'img', 'charts')
        os.makedirs(self.chart_directory, exist_ok=True)
    
    def generate_metrics_image(self, metrics_data, chart_type, hours=24):
        """Generate chart image for given metrics data."""
        if not metrics_data or 'history' not in metrics_data or not metrics_data['history']:
            logger.warning(f"No metrics data available for {chart_type} chart")
            return None
        if not metrics_data or not isinstance(metrics_data, dict) or 'history' not in metrics_data or not metrics_data['history']:
            logger.warning(f"No metrics data available for {chart_type} chart")
            return None
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            
            # Extract data points from history
            history = metrics_data['history']
            if not isinstance(history, list):
                logger.warning(f"History data is not a list: {type(history)}")
                return None
            timestamps = [entry.get('timestamp') for entry in history]


           

            if chart_type == 'latency':
                values = [entry.get('ping_ms', 0) for entry in history]
                title = 'Latency (ms)'
                color = 'blue'
            elif chart_type == 'packet_loss':
                values = [entry.get('packet_loss_percent', 0) for entry in history]
                title = 'Packet Loss (%)'
                color = 'red'
            elif chart_type == 'resources':
                values = [entry.get('resource_usage_percent', 0) for entry in history]
                title = 'Resource Usage (%)'
                color = 'green'
            else:
                logger.error(f"Unknown chart type: {chart_type}")
                return None
            
            # Create figure and plot
            plt.figure(figsize=(10, 4))
            plt.plot(timestamps, values, marker='o', linestyle='-', color=color, linewidth=2, markersize=4)
            
            # Set labels and title
            plt.title(f"{title} - Last {hours} hours")
            plt.xlabel('Time')
            plt.ylabel(title)
            
            # Format x-axis dates
            plt.gcf().autofmt_xdate()
            
            # Add grid
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Improve layout
            plt.tight_layout()
            
            # Save image to in-memory buffer
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            plt.close()
            
            # Encode image to base64
            buf.seek(0)
            img_data = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{img_data}"
            
        except ImportError:
            logger.warning("Matplotlib not available, cannot generate chart image")
            return None
        except Exception as e:
            logger.exception(f"Error generating chart image: {str(e)}")
            return None
    
    def generate_plotly_chart(self, metrics_data, chart_id, chart_type='combined'):
        """Generate interactive Plotly chart for server metrics."""
        if not metrics_data or 'history' not in metrics_data or not metrics_data['history']:
            logger.warning(f"No metrics data available for interactive chart")
            return None
        
        try:
            import plotly
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            # Extract data
            history = metrics_data['history']
            timestamps = [entry.get('timestamp') for entry in history]
            
            # Create figure with subplots
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Latency (ms)', 'Packet Loss (%)'),
                shared_xaxes=True,
                vertical_spacing=0.1
            )
            
            # Add traces
            latency = [entry.get('ping_ms', 0) for entry in history]
            packet_loss = [entry.get('packet_loss_percent', 0) for entry in history]
            
            # Add latency trace
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=latency,
                    mode='lines+markers',
                    name='Latency (ms)',
                    line=dict(color='blue', width=2)
                ),
                row=1, col=1
            )
            
            # Add packet loss trace
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=packet_loss,
                    mode='lines+markers',
                    name='Packet Loss (%)',
                    line=dict(color='red', width=2)
                ),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                height=600,
                showlegend=True,
                title_text="Server Performance Metrics",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # Add range slider
            fig.update_layout(
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(count=1, label="1h", step="hour", stepmode="backward"),
                            dict(count=6, label="6h", step="hour", stepmode="backward"),
                            dict(count=12, label="12h", step="hour", stepmode="backward"),
                            dict(count=1, label="1d", step="day", stepmode="backward"),
                            dict(step="all")
                        ])
                    ),
                    rangeslider=dict(visible=True),
                    type="date"
                )
            )
            
            # Convert to HTML
            chart_html = plotly.offline.plot(
                fig, 
                include_plotlyjs='cdn', 
                output_type='div',
                config={'responsive': True}
            )
            
            return chart_html
            
        except ImportError:
            logger.warning("Plotly not available, cannot generate interactive chart")
            return None
        except Exception as e:
            logger.exception(f"Error generating interactive chart: {str(e)}")
            return None