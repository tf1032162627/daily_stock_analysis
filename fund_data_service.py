# fund_data_service.py
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FundDataService:
    """基金数据服务类：获取净值、持仓、收益率等核心数据"""
    
    def __init__(self):
        # 设置中文显示
        pd.set_option('display.unicode.ambiguous_as_wide', True)
        pd.set_option('display.unicode.east_asian_width', True)

    def get_fund_net_value(self, fund_code):
        """获取基金单位净值走势（近1年）"""
        try:
            # AkShare基金净值接口
            df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
            # 数据清洗：转换日期和净值为正确格式
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
            # 只保留近1年数据
            one_year_ago = datetime.now() - timedelta(days=365)
            df = df[df['净值日期'] >= one_year_ago]
            return df
        except Exception as e:
            print(f"获取{fund_code}净值失败：{e}")
            return pd.DataFrame()

    def calculate_fund_return(self, fund_code):
        """计算基金阶段收益率（近1周/1月/3月/1年）"""
        df = self.get_fund_net_value(fund_code)
        if df.empty:
            return {"近1周": "无数据", "近1月": "无数据", "近3月": "无数据", "近1年": "无数据"}
        
        # 按日期排序
        df = df.sort_values('净值日期')
        latest_date = df['净值日期'].max()
        latest_net = df[df['净值日期'] == latest_date]['单位净值'].iloc[0]

        returns = {}
        # 计算各阶段收益率
        periods = {
            "近1周": latest_date - timedelta(days=7),
            "近1月": latest_date - timedelta(days=30),
            "近3月": latest_date - timedelta(days=90),
            "近1年": latest_date - timedelta(days=365)
        }

        for period_name, period_date in periods.items():
            # 找到该时间段最近的净值
            period_df = df[df['净值日期'] <= period_date]
            if not period_df.empty:
                period_net = period_df.iloc[-1]['单位净值']
                return_rate = (latest_net - period_net) / period_net * 100
                returns[period_name] = f"{return_rate:.2f}%"
            else:
                returns[period_name] = "数据不足"
        
        return returns

    def get_fund_portfolio(self, fund_code):
        """获取基金前10持仓股票/行业"""
        try:
            # AkShare基金持仓接口
            df = ak.fund_portfolio_hold_em(fund=fund_code)
            if df.empty:
                return "暂无持仓数据"
            # 提取前5持仓股票（简化展示）
            top5_hold = df.head(5)[['股票代码', '股票名称', '占净值比例']].to_string(index=False)
            return top5_hold
        except Exception as e:
            print(f"获取{fund_code}持仓失败：{e}")
            return "获取持仓失败"

    def calculate_risk_index(self, fund_code):
        """计算基金风险指标（最大回撤、夏普比率）"""
        df = self.get_fund_net_value(fund_code)
        if df.empty:
            return {"最大回撤": "无数据", "夏普比率": "无数据"}
        
        df = df.sort_values('净值日期')
        # 计算最大回撤
        df['累计最大值'] = df['单位净值'].cummax()
        df['回撤'] = (df['单位净值'] - df['累计最大值']) / df['累计最大值'] * 100
        max_drawdown = df['回撤'].min()  # 最大回撤是负数，代表下跌幅度

        # 计算夏普比率（简化版，无风险利率按3%年化）
        daily_returns = df['单位净值'].pct_change().dropna()
        if len(daily_returns) < 30:
            sharpe = "数据不足"
        else:
            daily_return_mean = daily_returns.mean()
            daily_return_std = daily_returns.std()
            # 年化夏普比率 = (日收益率均值*252 - 无风险利率) / (日收益率标准差*sqrt(252))
            sharpe = (daily_return_mean * 252 - 0.03) / (daily_return_std * np.sqrt(252)) if daily_return_std != 0 else 0
            sharpe = f"{sharpe:.2f}"

        return {
            "最大回撤": f"{max_drawdown:.2f}%",
            "夏普比率": sharpe
        }

    def get_fund_basic_info(self, fund_code):
        """获取基金基础信息（名称、类型）"""
        try:
            df = ak.fund_open_fund_info_em(fund=fund_code, indicator="基金基本信息")
            if df.empty:
                return {"基金名称": "未知", "基金类型": "未知"}
            # 提取关键信息
            name = df[df['项目'] == '基金全称']['值'].iloc[0] if '基金全称' in df['项目'].values else "未知"
            fund_type = df[df['项目'] == '基金类型']['值'].iloc[0] if '基金类型' in df['项目'].values else "未知"
            return {"基金名称": name, "基金类型": fund_type}
        except Exception as e:
            print(f"获取{fund_code}基础信息失败：{e}")
            return {"基金名称": "未知", "基金类型": "未知"}
