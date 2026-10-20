"""Episodic Rolling Hash Ring for zero-RAM conversational and edit history."""

from collections import deque
from dataclasses import dataclass
from typing import Optional
import time

from local_coder.knowledge.hyper_vector import HyperVector


@dataclass(frozen=True)
class DialogueTurn:
    """Represents an interaction turn in the coding session."""

    turn_id: int
    user_prompt: str
    assistant_response: str
    timestamp: float
    thought_vector: Optional[HyperVector] = None


class EpisodicRollingHashRing:
    """Bounded rolling ring buffer storing conversation turns with hypervectors."""

    def __init__(self, ring_capacity: int = 5, dimension: int = 10240) -> None:
        self.capacity = ring_capacity
        self.dimension = dimension
        self._turns: deque[DialogueTurn] = deque(maxlen=ring_capacity)
        self._archived_turns: list[DialogueTurn] = []
        self._turn_counter: int = 0

    @property
    def working_turns(self) -> list[DialogueTurn]:
        """Returns the active turns in the working ring."""
        return list(self._turns)

    @property
    def total_turn_count(self) -> int:
        """Returns total historical turns recorded."""
        return self._turn_counter

    def add_turn(
        self,
        user_prompt: str,
        assistant_response: str,
        thought_vector: Optional[HyperVector] = None,
    ) -> DialogueTurn:
        """Appends a new turn to the ring, archiving evicted turns into secondary storage."""
        self._turn_counter += 1
        if thought_vector is None:
            thought_vector = HyperVector.from_seed(user_prompt, dimension=self.dimension)

        turn = DialogueTurn(
            turn_id=self._turn_counter,
            user_prompt=user_prompt,
            assistant_response=assistant_response,
            timestamp=time.time(),
            thought_vector=thought_vector,
        )

        if len(self._turns) == self.capacity:
            evicted = self._turns[0]
            self._archived_turns.append(evicted)

        self._turns.append(turn)
        return turn

    def recall_relevant_turn(self, query: str) -> Optional[DialogueTurn]:
        """Recalls the most semantically relevant turn from memory via HyperVector similarity."""
        all_turns = self._archived_turns + list(self._turns)
        if not all_turns:
            return None

        query_vec = HyperVector.from_seed(query, dimension=self.dimension)
        best_turn: Optional[DialogueTurn] = None
        best_score = -1.0

        for turn in all_turns:
            if turn.thought_vector is not None:
                score = query_vec.similarity(turn.thought_vector)
                if score > best_score:
                    best_score = score
                    best_turn = turn

        return best_turn

    def clear(self) -> None:
        """Resets the memory ring."""
        self._turns.clear()
        self._archived_turns.clear()
        self._turn_counter = 0
