"""Declarative browser checks. Model-written JavaScript is never executed by Python/Node."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Step(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['add', 'delete', 'toggle', 'reload', 'expect_count', 'expect_title', 'expect_done']
    value: str = Field(default='', max_length=160)
    index: int = Field(default=0, ge=0, le=10)
    count: int = Field(default=0, ge=0, le=10)
    done: bool = True


class Requirement(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=3, max_length=100)
    steps: list[Step] = Field(min_length=3, max_length=16)

    @model_validator(mode='after')
    def meaningful(self):
        if not any(s.action.startswith('expect_') for s in self.steps):
            raise ValueError('验收要求必须包含实际断言')
        if not any(s.action == 'add' for s in self.steps):
            raise ValueError('检查应自行准备任务数据')
        return self


BASELINE_LABELS = {
    'add_toggle': '新增与勾选仍然可用',
    'duplicate_identity': '删除同名项，保留另一条记录',
    'mixed_order': '不同排列下只删除选中项',
    'persistence': '刷新后保留任务和完成状态',
}
