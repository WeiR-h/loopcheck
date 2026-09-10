"""Bounded, framework-independent acceptance contracts. No generated code execution."""
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, model_validator


def local_url(value: str) -> str:
    p = urlsplit(value)
    if p.scheme != 'http' or p.hostname not in {'localhost', '127.0.0.1', '::1'} or p.username or p.password or p.fragment:
        raise ValueError('Preview must be an http://localhost or loopback URL, without credentials or fragment')
    if not p.port:
        raise ValueError('Preview URL must include an explicit port')
    return value


class Locator(BaseModel):
    model_config = ConfigDict(extra='forbid')
    by: Literal['role', 'label', 'text', 'testid', 'placeholder']
    value: str = Field(min_length=1, max_length=160)
    name: str = Field(default='', max_length=160)


class BrowserStep(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['navigate', 'click', 'hover', 'fill', 'select', 'check', 'press', 'reload',
                    'expect_text', 'expect_value', 'expect_count', 'expect_visible', 'expect_checked', 'expect_url']
    target: Locator | None = None
    value: str = Field(default='', max_length=240)
    count: int = Field(default=0, ge=0, le=1000)
    checked: bool = True

    @model_validator(mode='after')
    def valid(self):
        if self.action not in {'navigate', 'reload', 'expect_url'} and not self.target:
            raise ValueError('This step needs an observed page locator')
        if self.action in {'navigate', 'expect_url'} and (not self.value.startswith('/') or self.value.startswith('//') or '\\' in self.value):
            raise ValueError('Navigation must be an absolute path on the selected preview origin')
        if self.action == 'press' and self.value not in {'Enter', 'Tab', 'Escape', 'ArrowDown', 'ArrowUp', 'Space'}:
            raise ValueError('Unsupported key')
        return self


class Flow(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=3, max_length=100)
    expectation: str = Field(min_length=3, max_length=400)
    purpose: Literal['preserve', 'new'] = 'preserve'
    steps: list[BrowserStep] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def meaningful(self):
        if not any(s.action.startswith('expect_') for s in self.steps):
            raise ValueError('Every flow needs an independent browser assertion')
        return self


class Proposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    flows: list[Flow] = Field(min_length=1, max_length=10)
