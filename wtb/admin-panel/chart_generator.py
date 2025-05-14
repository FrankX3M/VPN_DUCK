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
    def generate_metrics_image(self, metrics_data, chart_type='latency', hours=24):
        """Создает изображение графика на основе метрик
        
        Args:
            metrics_data: Данные метрик от API
            chart_type: Тип графика (latency, load, resources, packet_loss)
            hours: Количество часов для отображения
            
        Returns:
            Base64-закодированная строка изображения для встраивания в HTML
        """
        try:
            # Проверка наличия данных
            if not metrics_data:
                logger.warning("Нет данных для построения графика")
                return None
                
            if not isinstance(metrics_data, dict):
                logger.warning(f"Неверный тип данных метрик: {type(metrics_data)}")
                return None
                
            if 'history' not in metrics_data or not metrics_data['history']:
                logger.warning("Отсутствует история метрик в данных")
                return None
                
            # Импортируем matplotlib только при необходимости
            import matplotlib
            matplotlib.use('Agg')  # Использование не-интерактивного бэкенда
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from io import BytesIO
            import base64
            import datetime
            
            # Создаем фигуру с заданными размерами
            fig, ax = plt.subplots(figsize=(10, 5))
            
            # Обрабатываем и конвертируем временные метки
            history = metrics_data['history']
            timestamps = []
            values = []
            
            for item in history:
                if not isinstance(item, dict):
                    logger.debug(f"Пропуск элемента истории, не являющегося словарем: {item}")
                    continue
                    
                # Получаем временную метку - поддерживает разные форматы
                ts = item.get('timestamp', item.get('hour', None))
                if ts is None:
                    logger.debug(f"Пропуск элемента без временной метки: {item}")
                    continue
                    
                try:
                    # Пытаемся преобразовать строку в объект datetime
                    if isinstance(ts, str):
                        # Поддержка разных форматов времени
                        try:
                            dt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        except ValueError:
                            try:
                                dt = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                logger.debug(f"Невозможно разобрать формат времени: {ts}")
                                continue
                        timestamps.append(dt)
                    elif isinstance(ts, datetime.datetime):
                        timestamps.append(ts)
                    else:
                        logger.debug(f"Неподдерживаемый тип временной метки: {type(ts)}")
                        continue
                        
                    # Выбираем данные в зависимости от типа графика
                    if chart_type == 'latency':
                        value = item.get('avg_latency')
                        if value is None:
                            value = item.get('ping_ms')
                        if value is None:
                            value = item.get('latency', 0)
                        values.append(float(value))
                        
                    elif chart_type == 'packet_loss':
                        value = item.get('avg_packet_loss')
                        if value is None:
                            value = item.get('packet_loss_percent')
                        if value is None:
                            value = item.get('packet_loss', 0)
                        values.append(float(value))
                        
                    elif chart_type == 'load':
                        value = item.get('load')
                        if value is None:
                            value = item.get('server_load', 0)
                        values.append(float(value))
                        
                    elif chart_type == 'resources':
                        cpu_value = item.get('cpu_usage')
                        if cpu_value is None:
                            cpu_value = item.get('cpu', 0)
                        
                        memory_value = item.get('memory_usage')
                        if memory_value is None:
                            memory_value = item.get('memory', 0)
                            
                        values.append((float(cpu_value), float(memory_value)))
                        
                    else:
                        logger.warning(f"Неизвестный тип графика: {chart_type}")
                        return None
                        
                except (ValueError, TypeError) as e:
                    logger.debug(f"Ошибка обработки элемента данных: {e}, элемент: {item}")
                    continue
            
            # Проверяем, что у нас есть данные для построения
            if not timestamps or not values:
                logger.warning("Нет данных для построения графика после фильтрации")
                return None
                
            if len(timestamps) != len(values):
                logger.warning(f"Несоответствие длины массивов: timestamps={len(timestamps)}, values={len(values)}")
                # Обрезаем до минимальной длины
                min_length = min(len(timestamps), len(values))
                timestamps = timestamps[:min_length]
                values = values[:min_length]
            
            # Строим график в зависимости от типа
            if chart_type == 'latency':
                ax.plot(timestamps, values, 'b-', label='Latency (ms)')
                ax.set_ylabel('Latency (ms)')
                ax.set_title('Latency over last 24 hours')
                
            elif chart_type == 'load':
                ax.plot(timestamps, values, 'g-', label='Load (%)')
                ax.set_ylabel('Load (%)')
                ax.set_title('Server Load')
                ax.set_ylim(0, 100)
                
            elif chart_type == 'resources':
                # Разделяем значения CPU и памяти
                cpu_values = [v[0] for v in values]
                memory_values = [v[1] for v in values]
                
                ax.plot(timestamps, cpu_values, 'r-', label='CPU (%)')
                ax.plot(timestamps, memory_values, 'b-', label='Memory (%)')
                ax.set_ylabel('Usage (%)')
                ax.set_title('Resource Usage')
                ax.set_ylim(0, 100)
                ax.legend()
                
            elif chart_type == 'packet_loss':
                ax.plot(timestamps, values, 'r-', label='Packet Loss (%)')
                ax.set_ylabel('Packet Loss (%)')
                ax.set_title('Packet Loss')
                ax.set_ylim(0, max(5, max(values) * 1.2))  # Адаптивный масштаб
            
            # Форматирование оси X для отображения дат
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M\n%d.%m'))
            plt.xticks(rotation=0)
            
            # Добавляем сетку и легенду
            ax.grid(True, linestyle='--', alpha=0.7)
            if chart_type != 'resources':  # для resources легенда уже добавлена
                ax.legend()
            
            # Сохраняем график в память
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            
            # Кодируем как base64 для встраивания в HTML
            image_png = buffer.getvalue()
            buffer.close()
            plt.close(fig)  # Закрываем фигуру для освобождения памяти
            
            encoded = base64.b64encode(image_png).decode('utf-8')
            return encoded
        
        except ImportError as e:
            logger.exception(f"Ошибка импорта необходимых библиотек: {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"Ошибка генерации графика: {str(e)}")
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