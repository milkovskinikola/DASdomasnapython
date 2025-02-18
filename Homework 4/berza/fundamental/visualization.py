import io
import base64
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod

class ChartStrategy(ABC):
    @abstractmethod
    def create_chart(self, *args, **kwargs) -> str:
        pass
class PieChartStrategy(ChartStrategy):
    def create_chart(self, positive_percentage, negative_percentage, neutral_percentage) -> str:
        labels = ['Позитивни', 'Негативни', 'Неутрални']
        sizes = [positive_percentage, negative_percentage, neutral_percentage]
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']

        fig, ax = plt.subplots(figsize=(6,6))
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140, textprops=dict(color='w'))

        ax.axis('equal')
        ax.legend(wedges, labels, title="Знаци", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', bbox_inches='tight')
        plt.close(fig)
        img_buffer.seek(0)

        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')
        return img_base64


class BarChartStrategy(ChartStrategy):
    def create_chart(self, positive, negative, neutral) -> str:
        sentiments = ['Позитивни', 'Негативни', 'Неутрални']
        values = [positive, negative, neutral]
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(sentiments, values, color=colors)
        ax.set_ylabel('Вкупно', fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7, axis='y')

        for i, value in enumerate(values):
            ax.text(i, value + 0.5, str(value), ha='center', fontsize=12)

        plt.tight_layout()

        bar_buffer = io.BytesIO()
        plt.savefig(bar_buffer, format='png', bbox_inches='tight')
        plt.close(fig)
        
        bar_buffer.seek(0)
        
        bar_img_base64 = base64.b64encode(bar_buffer.read()).decode('utf-8')
        bar_buffer.close()

        return bar_img_base64
    
class ChartFactory:
    @staticmethod
    def get_chart_strategy(chart_type: str) -> ChartStrategy:
        if chart_type == "pie":
            return PieChartStrategy()
        elif chart_type == "bar":
            return BarChartStrategy()
        else:
            raise ValueError(f"Unknown chart type: {chart_type}")

def create_chart(chart_type, *args, **kwargs):
    chart_strategy = ChartFactory.get_chart_strategy(chart_type)
    return chart_strategy.create_chart(*args, **kwargs)


