from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypedDict


class UserInputConfirm(TypedDict):
    action: Literal["confirm"]
    scheme_index: int


class UserInputModify(TypedDict):
    action: Literal["modify"]
    modification_request: str


class UserInputProjectId(TypedDict):
    action: Literal["set_project_id"]
    project_id: str


UserInput = UserInputConfirm | UserInputModify | UserInputProjectId


@dataclass
class PendingSchemes:
    run_id: str
    product_name: str
    schemes: List[Dict[str, Any]]
    created_at: float


@dataclass
class PendingProjectId:
    run_id: str
    suggested_project_id: str
    created_at: float


class InteractionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._pending: Dict[str, PendingSchemes] = {}
        self._pending_project: Dict[str, PendingProjectId] = {}
        self._user_input: Dict[str, UserInput] = {}

    def set_pending(self, *, run_id: str, product_name: str, schemes: List[Dict[str, Any]]) -> None:
        with self._cv:
            self._pending[run_id] = PendingSchemes(
                run_id=run_id,
                product_name=product_name,
                schemes=schemes,
                created_at=time.time(),
            )
            # 清理旧输入，避免复用 run_id 时污染
            self._user_input.pop(run_id, None)
            self._cv.notify_all()

    def get_pending(self, run_id: str) -> Optional[PendingSchemes]:
        with self._lock:
            return self._pending.get(run_id)

    def set_pending_project_id(self, *, run_id: str, suggested_project_id: str = "") -> None:
        with self._cv:
            self._pending_project[run_id] = PendingProjectId(
                run_id=run_id,
                suggested_project_id=suggested_project_id,
                created_at=time.time(),
            )
            self._user_input.pop(run_id, None)
            self._cv.notify_all()

    def get_pending_project_id(self, run_id: str) -> Optional[PendingProjectId]:
        with self._lock:
            return self._pending_project.get(run_id)

    def submit(self, run_id: str, user_input: UserInput) -> None:
        with self._cv:
            if run_id not in self._pending:
                # 允许先提交后 pending（极端竞态），也会被 wait 消费
                self._pending[run_id] = PendingSchemes(
                    run_id=run_id, product_name="", schemes=[], created_at=time.time()
                )
            self._user_input[run_id] = user_input
            self._cv.notify_all()

    def wait_user_input(self, run_id: str, timeout_s: int) -> Optional[UserInput]:
        deadline = time.time() + max(0, timeout_s)
        with self._cv:
            while True:
                if run_id in self._user_input:
                    return self._user_input.pop(run_id)
                remain = deadline - time.time()
                if remain <= 0:
                    return None
                self._cv.wait(timeout=min(1.0, remain))

    def get_user_input(self, run_id: str) -> Optional[UserInput]:
        """获取并移除用户输入（非阻塞，用于异步轮询）"""
        with self._lock:
            return self._user_input.pop(run_id, None)

    def clear(self, run_id: str) -> None:
        with self._cv:
            self._pending.pop(run_id, None)
            self._pending_project.pop(run_id, None)
            self._user_input.pop(run_id, None)
            self._cv.notify_all()


interaction_store = InteractionStore()

