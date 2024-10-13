from typing import List, Optional
from game import Bot, GameState, Move, PlayerPerspective, SchnapsenTrickScorer
from deck import Card, Suit, Rank
from game import Move as SchnapsenMove, RegularMove, Marriage, TrumpExchange, GamePlayEngine
import random
from random import Random
from game import GamePhase

class LowRiskBotFinal(Bot):
    def __init__(self, rand: random.Random, num_samples:int, depth: int, name: str = "LowRiskBotFinal", risk_tolerance: float = 0.3):
        """
        Create a new low risk bot.

        :param num_samples: how many samples to take per move
        :param risk_tolerance: a constant that make every move a low risk to take
        :param rand: the source of randomness for this Bot
        :param name: the name of this bot
        """
        super().__init__(name)
        assert num_samples >= 1, f"we cannot work with less than one sample, got {num_samples}"
        assert depth >= 1, f"it does not make sense to use a depth <1. got {depth}"
        self.risk_tolerance = risk_tolerance
        self.name = name
        self.my_past_moves = []  # An emptylist is created where all the past moves of this bot are stored.
        self.opponent_past_moves = []  #An empty list is created where all the past moves of the opponent are stored.
        self.num_samples = num_samples #How many samples the bot should take per move
        self.depth = depth #How deep the bot has to sample
        self.rand = rand

    def get_move(self, perspective: PlayerPerspective, leader_move: Optional[Move]) -> Move:
        """
        Determines the next move of the player, depending on whether they play leading or following.
        """
        moves = perspective.valid_moves() #Gets the list of the valid_moves of current player
        self.rand.shuffle(moves) #Shuffles list of valid_moves to make the bot choose randomly

        if leader_move is None:  #Bot checks if they are the leader.
            chosen_move = self.evaluate_moves_as_leader(moves, perspective) #The next move for the bot as the leader is determined.
        else:  #Bot is not leader so leads from here as the follower.
            chosen_move = self.evaluate_moves_as_follower(moves, perspective, leader_move) #The next move for the bot as the follower is determined.

        self.my_past_moves.append(chosen_move) #The move that the bot plays, will be put in the list to keep track of the played moves.
        return chosen_move
    
    def notify_trump_exchange(self, move: TrumpExchange) -> None:
        """
        Stores opponent's trump exchange move.
        """
        self.opponent_past_moves.append(move) #Adds trump exchange move of the opponent to the list of past moves.

    def notify_game_end(self, won: bool, perspective: PlayerPerspective) -> None:
        """
        Resets the game after a win.
        """
        self.adjust_risk_parameters(won) #Readjusts risk parameters if bot won game. 

        self.my_past_moves = [] #Cleans the list from past moves and resets it to an empty list
        self.opponent_past_moves = [] #Cleans the list from opponent's past moves and resets it to an empty list.

    def adjust_risk_parameters(self, won: bool):
        """
        Readjusts risk parameters after a game has ended. 
        Risk tolerance increases after a win and decreases after a loss.
        """
        if won: 
            self.risk_tolerance += 0.1  #Increase risk tolerance after a win, so the next game will be played with a slightly greater risk.
        else:
            self.risk_tolerance -= 0.05  #Decrease risk tolerance after a loss, so the next game will be plated with a slightly smallet risk.
        self.risk_tolerance = max(0, min(self.risk_tolerance, 1))  #Keep risk tolerance between 0 and 1.


    def evaluate_moves_as_leader(self, moves, perspective):
        """
        Evaluates list of moves.
        Returns best move with the highest gain of score.
        """
        best_move = None
        best_net_gain = float('-inf') #Best net gain is initialised with negative infinity, so the first move is always better than the ones after.
        opponents_potential_score = self.estimate_opponents_potential_score(perspective) #Oppononent's potential score is being calculated

        for move in moves:
            net_gain = 0 #Initialising net gain to 0.
            for _ in range(self.num_samples):
                gamestate = perspective.make_assumption(leader_move=None, rand=self.rand) #A new game state is created, based on perspective and random.
                reward = self._evaluate_points_accumulated(gamestate, move) #Calculates reward for played move.
                risk = self.evaluate_risk(gamestate, move) #Calculates risk for played move.

                net_gain += (reward - risk) - opponents_potential_score #Calculates what the player will earn with the played move by substracting the risk from the reward and readjust the opponent's potential score.
            if net_gain > best_net_gain: #Compare if net_gain is greater than best_net_gain and if so continue.
                best_net_gain = net_gain #Adjust value of best_net_gain.
                best_move = move #Adjust value of best_move.

        return best_move 

    def evaluate_moves_as_follower(self, moves, perspective, leader_move):
        """
        Evaluates every move the player could make as the follower based on the move of the leader and 
        returns the move that will result into a win for the player with the highest points. It takes 
        into consideration every move the opponent can make and calculates an average score.
        Returns best move as a following plater based on the calculations.
        """
        chosen_move = None
        best_score = float('-inf') #Best_score is initialised with negative infinity, so the first move is always better than the ones after.
        opponents_potential_score = self.estimate_opponents_potential_score(perspective) #Oppononent's potential score is being calculated

        for move in moves:
            score = 0 #Initialising score to 0.
            for _ in range(self.num_samples):
                gamestate = perspective.make_assumption(leader_move=leader_move, rand=self.rand) #A new game state is created, based on perspective and random.
                reward = self._evaluate_points_accumulated(gamestate, move) #Calculates reward for played move.
                risk = self.evaluate_risk(gamestate, move) #Calculates risk for played move.

                score += (reward - risk) - opponents_potential_score #Calculates what the player will earn with the played move by substracting the risk from the reward and readjust the opponent's potential score.
            if score > best_score: #Compare if score is greater than best_score and if so continue.
                best_score = score #Adjust value of best_score.
                chosen_move = move #Adjust value of chosen_move.

        return chosen_move

    def _evaluate_points_accumulated(self, gamestate: GameState, move: Move) -> int:
        """"        
        Evaluates points the player collected during the game in a given state.
        Returns a score that player gets according to the evaluation.
        """
        scorer = SchnapsenTrickScorer()
        score = 0 #Initializes score to 0
        if isinstance(move, RegularMove):
            score += scorer.rank_to_points(move.card.rank) #Calculates the points of the card by rank.
        elif isinstance(move, Marriage):
            marriage_score = scorer.marriage(move, gamestate) #Checks if there is a marriage.
            score += marriage_score.pending_points #If there is a marriage, adds those points.
        return score
    
    def estimate_opponents_potential_score(self, perspective: PlayerPerspective) -> float:
        """
        Calculates the potential score of the opponent based on the tricks they won and the potential
        cards they have, what is still unknown for the player.
        Returns estimated points of the opponent based on the calulations and previous won tricks.
        """
        estimated_score = 0
        scorer = SchnapsenTrickScorer()

        for card in perspective.get_opponent_won_cards(): 
            estimated_score += scorer.rank_to_points(card.rank) #Adds the points of the card by rank to the estimated_score.

        if perspective.get_phase() == GamePhase.TWO:
            unknown_cards_count = len(perspective.get_opponent_hand_in_phase_two()) - len(perspective.get_known_cards_of_opponent_hand()) #Calculates the number of unknown cards in hand of opponent in phase two.
            average_card_value = self.get_average_value_card(perspective) #Calculates average of the cards in opponents hand.
            estimated_score += unknown_cards_count * average_card_value #Adds estimated points from the unknown cards from the opponent to estimated_score.

        estimated_score += self.estimate_marriage_points(perspective) #Adds potential points from marriages to the estimated_score.

        return estimated_score

    def get_average_value_card(self, perspective: PlayerPerspective) -> float:
        """
        Calculate the average value of the remaining cards in the deck.
        Returns the average point value of unseen cards.
        """
        scorer = SchnapsenTrickScorer()
        initial_deck = perspective.get_engine().deck_generator.get_initial_deck()
        seen_cards = perspective.seen_cards(None)

        unseen_cards = [card for card in initial_deck if card not in seen_cards] #Calculates the difference between intial_deck and seen_cards manually.

        total_points = sum(scorer.rank_to_points(card.rank) for card in unseen_cards)
        return total_points / len(unseen_cards) if unseen_cards else 0

    def estimate_marriage_points(self, perspective: PlayerPerspective) -> int:
        """
        Estimate points the opponent might gain from marriages.
        Returns estimated points from potential marriages.
        """
        estimated_marriage_points = 0
        scorer = SchnapsenTrickScorer()

        if perspective.get_phase() != GamePhase.TWO: #Chechs if current game phase is not phase two.
            return 0  # Returns 0 if it's not phase two.

        potential_marriages = {suit: False for suit in Suit} #Creates a dictionary with suits as key and false as their values, to see which suits are left as potential marriages.

        for card in perspective.get_opponent_won_cards(): #Looks through opponent's cards which they won.
            if card.rank in [Rank.QUEEN, Rank.KING]: #Checks the rank of the cards whether they are a King or Queen.
                potential_marriages[card.suit] = True #Sets the value of said suit to True in the dictionary.

    # Estimate points for potential marriages
        for suit, potential in potential_marriages.items():
            if potential:
                queen_card = Card.get_card(Rank.QUEEN, suit)
                king_card = Card.get_card(Rank.KING, suit)
                marriage = Marriage(queen_card, king_card)
                marriage_points = scorer.marriage(marriage, perspective.get_state_in_phase_two()).pending_points #Calculates the points for the potential marriage.
                estimated_marriage_points += marriage_points * 0.5  #Adds estimated points to estimated_points_marriage.

        return estimated_marriage_points
    
    def evaluate_risk(self, gamestate: GameState, move: Move) -> float:
        """
        Evaluate the risk of a move, considering both the consequence and the probability of that consequence.

        Returns a risk score where a higher score indicates higher risk.
        """
        probability_of_consequence = self.estimate_probability_of_consequence(gamestate, move)
        consequence_severity = self.estimate_consequence_severity(gamestate, move)

        # Modify the risk calculation to use self.risk_tolerance
        risk_score = consequence_severity * probability_of_consequence * self.risk_tolerance

        return risk_score

    def estimate_probability_of_consequence(self, gamestate: GameState, move: Move) -> float:
        """
        Estimate the probability of an adverse outcome occurring as a result of the move.
        """
        opponent_hand = gamestate.follower.hand #Gets the opponent's hand.

        if isinstance(move, RegularMove):
            higher_cards = [card for card in opponent_hand if card.rank.value > move.card.rank.value] #Gets list of card in opponent's hand that are higher than the rank of the card in 'move'.
            return len(higher_cards) / len(opponent_hand) if opponent_hand else 0 #Returns probability of being beaten by opponent based on the cards in 'move'.

        elif isinstance(move, Marriage):
            same_suit_cards = [card for card in opponent_hand if card.suit == move.suit and card.rank.value > Rank.QUEEN.value] #Creates a list of the cards in the opponent's hand with the same suit as the card in 'move' and a higher rank than Queen.
            trump_cards = [card for card in opponent_hand if card.suit == gamestate.trump_suit] #Gets a list of trump cards in the opponent's hand.
            return (len(same_suit_cards) + len(trump_cards)) / len(opponent_hand) if opponent_hand else 0 #Returns probability of being beaten by opponent based on the higher cards and the amount of trump cards in opponent's hand compared to card in 'move'.

        elif isinstance(move, TrumpExchange):

            return 0.3

        return 0.5  #Unhandled moves get a default of 0.5

    def estimate_consequence_severity(self, gamestate: GameState, move: Move) -> float:
        """
        Estimate the severity of the consequence if the adverse outcome occurs.
        """
        scorer = SchnapsenTrickScorer()

        if isinstance(move, RegularMove):
            return scorer.rank_to_points(move.card.rank)

        elif isinstance(move, Marriage):
            marriage_score = scorer.marriage(move, gamestate) #Calculates score for marriage based on gamestate during that move.
            return marriage_score.pending_points

        elif isinstance(move, TrumpExchange):
            return 1 #TrumpExchange get a lower severity
        
        return 0  #Unhandled moves get a default of 1
