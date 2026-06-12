"""
Pydantic models for Week 2 extraction: subscription_flow and equity_snapshot.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, Union
from datetime import date


class SubscriptionFlow(BaseModel):
    """认缴流量：谁在什么时候认购了多少、多少钱、什么价格。"""
    record_type: Literal["subscription_flow"] = "subscription_flow"
    stock_code: str = Field(..., description="股票代码，如 603418")
    company_name: str = Field(..., description="公司简称")
    pdf_page: Union[int, str] = Field(..., description="PDF 页码")
    subscription_date: Optional[str] = Field(None, description="增资日期，YYYY-MM-DD")
    batch_label: Optional[str] = Field(None, description="批次标签，如 第1批")
    subscriber_name: str = Field(..., description="认购方名称")
    subscription_shares_wan: Optional[float] = Field(None, description="认购数量(万股)")
    subscription_amount_wan: Optional[float] = Field(None, description="认购金额(万元)")
    subscription_price_yuan: Optional[float] = Field(None, description="认购价格(元/股)")
    evidence_text: str = Field(..., description="PDF 原文证据片段")
    notes: Optional[str] = Field(None, description="备注说明")

    @field_validator("subscription_date")
    @classmethod
    def validate_date(cls, v):
        if v is not None and v.strip():
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError(f"日期格式无效: {v}，应为 YYYY-MM-DD")
        return v

    @field_validator("subscription_shares_wan", "subscription_amount_wan", "subscription_price_yuan", mode="before")
    @classmethod
    def coerce_numeric(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            v = v.strip().rstrip("%")
            try:
                return float(v)
            except ValueError:
                raise ValueError(f"无法转换为数值: {v}")
        return v


class EquitySnapshot(BaseModel):
    """股权结构存量：某个时点股东结构。"""
    record_type: Literal["equity_snapshot"] = "equity_snapshot"
    stock_code: str = Field(..., description="股票代码")
    company_name: str = Field(..., description="公司简称")
    pdf_page: Union[int, str] = Field(..., description="PDF 页码")
    time_point: str = Field(..., description="时点标签，如 t0/报告期初")
    equity_structure_scope: Optional[str] = Field(None, description="股权结构口径说明")
    total_shares_wan: Optional[float] = Field(None, description="总股本(万股)")
    total_capital_wan: Optional[float] = Field(None, description="总出资额(万元注册资本)")
    shareholder_name: str = Field(..., description="股东名称")
    shares_held_wan: Optional[float] = Field(None, description="持股数(万股)")
    capital_contribution_wan: Optional[float] = Field(None, description="出资额(万元注册资本)")
    shareholding_ratio: Optional[float] = Field(None, description="持股比例")
    evidence_text: str = Field(..., description="PDF 原文证据片段")
    notes: Optional[str] = Field(None, description="备注说明")

    @field_validator("shareholding_ratio", mode="before")
    @classmethod
    def coerce_ratio(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            v = v.strip().rstrip("%")
            try:
                return float(v)
            except ValueError:
                raise ValueError(f"持股比例无法转换: {v}")
        return v

    @field_validator("shareholding_ratio")
    @classmethod
    def validate_ratio(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError(f"持股比例应在 0-100 之间: {v}")
        return v

    @field_validator("total_shares_wan", "total_capital_wan", "shares_held_wan", "capital_contribution_wan", mode="before")
    @classmethod
    def coerce_numeric(cls, v):
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            v = v.strip().rstrip("%")
            try:
                return float(v)
            except ValueError:
                raise ValueError(f"无法转换为数值: {v}")
        return v
