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
        if not metrics_data or not isinstance(metrics_data, dict) or 'history' not in metrics_data or not metrics_data['history']:
            logger.warning(f"No metrics data available for {chart_type} chart")
            return None
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend
            import matplotlib.pyplot as plt
            
            # Extract data points from history
            history = metrics_data['history']
            
            # Проверка типа данных
            if not isinstance(history, list):
                logger.warning(f"History data is not a list: {type(history)}")
                return None
                
            # Безопасное извлечение временных меток и обработка различных форматов
            timestamps = []
            for item in history:
                if isinstance(item, dict):
                    ts = item.get('timestamp', item.get('hour', ''))
                    if ts:
                        if isinstance(ts, str):
                            try:
                                # Попытка преобразовать строку в datetime
                                ts = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
                            except ValueError:
                                try:
                                    ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    # Оставляем как есть, если не удалось преобразовать
                                    pass
                        timestamps.append(ts)
                
            if not timestamps:
                logger.warning("No timestamps found in history data")
                return None
                
            # Безопасное извлечение значений в зависимости от типа графика
            values = []
            title = ""
            color = "blue"
            
            if chart_type == 'latency':
                values = [entry.get('avg_latency', entry.get('ping_ms', 0)) 
                         for entry in history if isinstance(entry, dict)]
                title = 'Latency (ms)'
                color = 'blue'
            elif chart_type == 'packet_loss':
                values = [entry.get('avg_packet_loss', entry.get('packet_loss_percent', 0)) 
                         for entry in history if isinstance(entry, dict)]
                title = 'Packet Loss (%)'
                color = 'red'
            elif chart_type == 'resources':
                values = [entry.get('cpu_usage', entry.get('resource_usage_percent', 0)) 
                         for entry in history if isinstance(entry, dict)]
                title = 'Resource Usage (%)'
                color = 'green'
            else:
                logger.error(f"Unknown chart type: {chart_type}")
                return None
                
            # Проверяем наличие пустых или None значений
            values = [v if v is not None else 0 for v in values]
                
            if len(values) != len(timestamps):
                logger.warning(f"Mismatch between timestamps ({len(timestamps)}) and values ({len(values)})")
                # Обрезаем до минимальной длины
                min_length = min(len(timestamps), len(values))
                timestamps = timestamps[:min_length]
                values = values[:min_length]
                
            if not values:
                logger.warning("No values found for chart")
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
        if not metrics_data or not isinstance(metrics_data, dict) or 'history' not in metrics_data or not metrics_data['history']:
            logger.warning(f"No metrics data available for interactive chart")
            return None
        
        try:
            import plotly
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            # Extract data
            history = metrics_data['history']
            
            # Проверка типа данных
            if not isinstance(history, list):
                logger.warning(f"History data is not a list for interactive chart: {type(history)}")
                return None
            
            # Безопасное извлечение временных меток
            timestamps = []
            for item in history:
                if isinstance(item, dict):
                    ts = item.get('timestamp', item.get('hour', ''))
                    if ts:
                        if isinstance(ts, str):
                            try:
                                # Попытка преобразовать строку в datetime
                                ts = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
                            except ValueError:
                                try:
                                    ts = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    # Оставляем как есть, если не удалось преобразовать
                                    pass
                        timestamps.append(ts)
            
            if not timestamps:
                logger.warning("No timestamps found for interactive chart")
                return None
            
            # Безопасное извлечение значений для графиков
            latency = [entry.get('avg_latency', entry.get('ping_ms', 0)) 
                      for entry in history if isinstance(entry, dict)]
            packet_loss = [entry.get('avg_packet_loss', entry.get('packet_loss_percent', 0)) 
                          for entry in history if isinstance(entry, dict)]
            resource_usage = [entry.get('cpu_usage', entry.get('resource_usage_percent', 0)) 
                             for entry in history if isinstance(entry, dict)]
            
            # Проверяем наличие пустых или None значений
            latency = [v if v is not None else 0 for v in latency]
            packet_loss = [v if v is not None else 0 for v in packet_loss]
            resource_usage = [v if v is not None else 0 for v in resource_usage]
            
            # Проверяем соответствие длин массивов
            min_length = min(len(timestamps), len(latency), len(packet_loss), len(resource_usage))
            if min_length == 0:
                logger.warning("No valid data points for interactive chart")
                return None
                
            timestamps = timestamps[:min_length]
            latency = latency[:min_length]
            packet_loss = packet_loss[:min_length]
            resource_usage = resource_usage[:min_length]
            
            # Create figure with subplots
            if chart_type == 'combined':
                # Полный график с тремя параметрами
                fig = make_subplots(
                    rows=3, cols=1,
                    subplot_titles=('Latency (ms)', 'Packet Loss (%)', 'Resource Usage (%)'),
                    shared_xaxes=True,
                    vertical_spacing=0.1
                )
                
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
                
                # Add resource usage trace
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=resource_usage,
                        mode='lines+markers',
                        name='Resource Usage (%)',
                        line=dict(color='green', width=2)
                    ),
                    row=3, col=1
                )
                
                fig_height = 800  # Большая высота для трех графиков
            else:
                # Упрощенный график с двумя параметрами
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=('Latency (ms)', 'Packet Loss (%)'),
                    shared_xaxes=True,
                    vertical_spacing=0.1
                )
                
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
                
                fig_height = 600  # Стандартная высота для двух графиков
            
            # Update layout
            fig.update_layout(
                height=fig_height,
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