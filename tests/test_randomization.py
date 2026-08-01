import random
import unittest
from collections import Counter

from randomization import constrained_shuffle


class ConstrainedShuffleTests(unittest.TestCase):
    def test_balance_and_run_length(self):
        tasks = ["grasp", "handover", "place", "press"]
        sequence = constrained_shuffle(
            tasks,
            repetitions_per_task=10,
            max_same_in_row=2,
            rng=random.Random(42),
        )
        self.assertEqual(Counter(sequence), Counter({task: 10 for task in tasks}))
        for index in range(len(sequence) - 2):
            self.assertFalse(sequence[index] == sequence[index + 1] == sequence[index + 2])


if __name__ == "__main__":
    unittest.main()
