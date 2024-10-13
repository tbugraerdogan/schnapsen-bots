import random
from game import Bot, PlayerPerspective, Move, GameState, TrumpExchange, RegularMove, Marriage, SchnapsenTrickScorer, GamePhase
from deck import Card, Suit, Rank
from typing import Optional

class MidRiskBot(Bot):
    def __init__(self, rand: random.Random, num_samples: int, depth: int, name: str = "MidRiskBot", risk_tolerance: float = 0.55):
        super().__init__(name)
        self.risk_tolerance = risk_tolerance
        self.rand = rand
        self.num_samples = num_samples
        self.depth = depth
        self.my_past_moves = []
        self.opponent_past_moves = []

    def get_move(self, perspective: PlayerPerspective, leader_move: Optional[Move]) -> Move:
        moves = perspective.valid_moves()
        self.rand.shuffle(moves)

        best_move = None
        best_net_gain = float('-inf')

        for move in moves:
            net_gain = 0
            for _ in range(self.num_samples):
                gamestate = perspective.make_assumption(leader_move=None, rand=self.rand)
                reward = self._evaluate_points_accumulated(gamestate, move)
                risk = self.evaluate_risk(gamestate, move)

                net_gain += (reward - risk)

            average_net_gain = net_gain / self.num_samples
            if average_net_gain > best_net_gain:
                best_net_gain = average_net_gain
                best_move = move

        return best_move

    def notify_trump_exchange(self, move: TrumpExchange) -> None:
        self.opponent_past_moves.append(move)

    def notify_game_end(self, won: bool, perspective: PlayerPerspective) -> None:
        if won: 
            self.risk_tolerance = min(self.risk_tolerance + 0.05, 1)
        else:
            self.risk_tolerance = max(self.risk_tolerance - 0.05, 0)
        self.my_past_moves = []
        self.opponent_past_moves = []

    def _evaluate_points_accumulated(self, gamestate: GameState, move: Move) -> int:
        scorer = SchnapsenTrickScorer()
        score = 0
        if isinstance(move, RegularMove):
            score += scorer.rank_to_points(move.card.rank)
        elif isinstance(move, Marriage):
            marriage_score = scorer.marriage(move, gamestate)
            score += marriage_score.pending_points
        return score

    def evaluate_risk(self, gamestate: GameState, move: Move) -> float:
        probability_of_consequence = self.estimate_probability_of_consequence(gamestate, move)
        consequence_severity = self.estimate_consequence_severity(gamestate, move)
        risk_score = consequence_severity * probability_of_consequence * self.risk_tolerance
        return risk_score

    def estimate_probability_of_consequence(self, gamestate: GameState, move: Move) -> float:
        opponent_hand = gamestate.follower.hand
        if isinstance(move, RegularMove):
            higher_cards = [card for card in opponent_hand if card.rank.value > move.card.rank.value]
            return len(higher_cards) / len(opponent_hand) if opponent_hand else 0
        elif isinstance(move, Marriage):
            same_suit_cards = [card for card in opponent_hand if card.suit == move.suit and card.rank.value > Rank.QUEEN.value]
            trump_cards = [card for card in opponent_hand if card.suit == gamestate.trump_suit]
            return (len(same_suit_cards) + len(trump_cards)) / len(opponent_hand) if opponent_hand else 0
        elif isinstance(move, TrumpExchange):
            return 0.3
        return 0.5  # Default probability for unhandled move types
    
    def estimate_consequence_severity(self, gamestate: GameState, move: Move) -> float:
        scorer = SchnapsenTrickScorer()
        if isinstance(move, RegularMove):
            return scorer.rank_to_points(move.card.rank)
        elif isinstance(move, Marriage):
            marriage_score = scorer.marriage(move, gamestate)
            return marriage_score.pending_points
        elif isinstance(move, TrumpExchange):
            return 1
        return 0  # Default severity for unhandled move types

