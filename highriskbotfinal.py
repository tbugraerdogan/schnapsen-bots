import random
from game import Bot, PlayerPerspective, TrumpExchange, RegularMove, Marriage, SchnapsenTrickScorer, GameState, Move
from deck import Rank, Card, Suit
from random import Random
from typing import List, Optional

class HighRiskBotFinal(Bot):
    """
    High-risk bot is a bot which performs many random rollouts of the game to decide which move will make the bot gain as many points as possible with 
    """
    def __init__(self, rand: Random, num_samples: int, depth: int, name: str = "HighRiskBotFinal", risk_tolerance: float = 0.8):
        """
        Create a new high risk bot.

        :param num_samples: how many samples to take per move
        :param risk_tolerance: a constant that make every move a high risk to take
        :param rand: the source of randomness for this Bot
        :param name: the name of this bot
        """
        super().__init__(name)
        assert num_samples >= 1, f"we cannot work with less than one sample, got {num_samples}"
        assert depth >= 1, f"it does not make sense to use a depth <1. got {depth}"
        self.risk_tolerance = risk_tolerance
        self.my_past_moves = [] # An emptylist is created where all the past moves of this bot are stored.
        self.opponent_past_moves = [] #An empty list is created where all the past moves of the opponent are stored.
        self.rand = rand
        self.num_samples = num_samples #How many samples the bot should take per move
        self.depth = depth #How deep the bot has to sample

    def get_move(self, perspective: PlayerPerspective, leader_move: Optional[Move]) -> Move:
        """
        Gets the list of valid moves and shuffles it, that it gets the move with the highest reward. 
        Returns the best possible move.
        """
        moves = list(perspective.valid_moves()) 
        self.rand.shuffle(moves) #Shuffles list of valid_moves to make the bot choose randomly
        high_rewarded_value = [self.__high_reward_evaluation(perspective, move) for move in moves]
        best_high_reward = max(high_rewarded_value)
        best_move = moves[high_rewarded_value.index(best_high_reward)]
        return best_move

    def notify_trump_exchange(self, move: TrumpExchange) -> None:
        """
        The engine will call this method when a trump exchange is made.
        Adds the trump exchange move that the opponent uses to the list of moves the opponent made.
        """
        self.opponent_past_moves.append(move) #Adds trump exchange move of the opponent to the list of past moves.

    def notify_game_end(self, won: bool, perspective: PlayerPerspective) -> None:
        """
        Calls recalculate_risk_parameters to use the readjusted risk_tolerance for the next game.
        Resets both own and opponents past moves to an empty list.
        """
        self.recalculate_risk_parameters(won) #Readjusts risk parameters if bot won game. 
        self.my_past_moves = [] #Cleans the list from past moves and resets it to an empty list
        self.opponent_past_moves = [] #Cleans the list from opponent's past moves and resets it to an empty list.

    def recalculate_risk_parameters(self, won: bool):
        """
        Readjusts risk parameters after a game has ended. 
        Risk tolerance increases after a win and decreases after a loss.
        """
        if won: 
            self.risk_tolerance += 0.05  #Increase risk tolerance after a win, so the next game will be played with a slightly greater risk.
        else:
            self.risk_tolerance -= 0.05  #Decrease risk tolerance after a loss, so the next game will be plated with a slightly smallet risk.
        self.risk_tolerance = max(0, min(self.risk_tolerance, 1))  #Keep risk tolerance between 0 and 1.


    def __high_reward_evaluation(self, perspective: PlayerPerspective, move: Move) -> float:
        """
        Evaluates the gain of a certain move.
        Returns amount of total points gained by playing a certain card.
        """
        rewarded_value = 0

        if isinstance(move, RegularMove):
            rewarded_value += self.calculated_points_card(move.card)
        elif isinstance(move, Marriage):
            if move.suit == perspective.get_trump_suit() and move.queen_card.rank == Rank.QUEEN and move.king_card.rank == Rank.KING:
                rewarded_value += 40
            else:
                rewarded_value += 20

        return rewarded_value



    def calculated_points_card(self, card: Card) -> int:
        """
        Calculates the points the winner of the trick gets.
        Returns the points that the cards in the trick will give the winner.
        """
        points = {Rank.ACE: 11, Rank.TEN: 10, Rank.KING: 4, Rank.QUEEN: 3, Rank.JACK: 2}
        return points.get(card.rank, 0)

    def is_marriage_high_reward(self, gamestate, move):
        """
        Calculates the points the player with a marriage gets, depending on what type of marriage it is.
        Returns 20 points for regular marriage and 40 for royal, only if there is a marriage.
        """
        if isinstance(move, Marriage):
            marriage_score = SchnapsenTrickScorer().marriage(move, gamestate)
            return marriage_score.pending_points >= 20 or (marriage_score.pending_points == 20 and move.suit == gamestate.trump_suit and move.card_one.rank == Rank.KING and move.card_two.rank == Rank.QUEEN)
        return False

    def simulate_move(self, current_state: GameState, next_move: Move) -> GameState:
        """
        Predicts the state of the game after the next move, without actually performing the move.
        Returns the hypothetical state of the game.

        :param current_state: GameState object representing the current state of the game.
        :param next_move: Move object representing the next move to be simulated.
        :returns: GameState object representing the predicted state after the move.
        """
        simulated_state = current_state.copy_for_next()  # Cloning the current game state to a new object.
        if isinstance(next_move, TrumpExchange):
            # Simulating a trump exchange.
            simulated_state.talon.trump_exchange(next_move.jack)
        elif isinstance(next_move, Marriage):
            # Simulating a marriage.
            simulated_state.leader.hand.remove(next_move.queen_card)
            simulated_state.leader.hand.remove(next_move.king_card)
        else:
            # Simulating a regular move.
            simulated_state.leader.hand.remove(next_move.cards)

        return simulated_state

    def calculate_score(self, gamestate: GameState) -> int:
        """
        Calculate the total points of the player up to the current state of the game.
        Uses the GameState to determine the points accumulated from won tricks and marriages.

        :param gamestate: The current state of the game.
        :returns: The total score of the player.
        """
        score = 0
        scorer = SchnapsenTrickScorer()

        # Points from tricks won
        for card in gamestate.leader.won_cards:  # Assuming 'self' is the leader; change to follower if needed
            score += scorer.rank_to_points(card.rank)

        # Points from marriages
        for card in gamestate.leader.won_cards:  # Assuming 'self' is the leader; change to follower if needed
            if card.rank in [Rank.KING, Rank.QUEEN]:
                marriage_score = scorer.marriage(Marriage(Card(Rank.QUEEN, card.suit), Card(Rank.KING, card.suit)), gamestate)
                score += marriage_score.pending_points

        return score
    
    def evaluate_moves_as_leader(self, moves, gamestate, perspective):
        """
        Evaluates every move the player could make as the leader and returns the move that will result
        into a win for the player with the highest points. It takes into consideration every move the opponent
        can make and calculates an average score.
        Returns best move as a leading player based on the calculations.
        """
        best_move = None
        best_score = float('-inf') #Total score is initialised with negative infinity, so the first move is always better than the ones after.

        for move in moves:
            total_score = 0 #Initialising best_move to 0.
            for _ in range(self.num_samples):
                simulated_gamestate = self.simulate_move(gamestate, move) #Simulates state after move.
                score = self.calculate_score(simulated_gamestate)
                risk = self.evaluate_risk(simulated_gamestate, move)
                total_score += (score - risk)

                if self.is_marriage_high_reward(simulated_gamestate, move):
                    score += 20 #High reward marriage will add 20 points to the score.

                if isinstance(move, RegularMove):
                    score += self.calculated_points_card(move.card)

                opponent_potential = self.estimate_opponents_potential_score(perspective)
                total_score += score - opponent_potential

            average_score = total_score / self.num_samples
            if average_score > best_score: #Compare if average_score is greater than total_score and if so continue.
                best_score = average_score #Adjust value of total_score.
                best_move = move #Adjust value of best_move.

        return best_move

    def evaluate_moves_as_follower(self, moves, perspective, gamestate, leader_move):
        """
        Evaluates every move the player could make as the follower based on the move of the leader and 
        returns the move that will result into a win for the player with the highest points. It takes 
        into consideration every move the opponent can make and calculates an average score.
        Returns best move as a following plater based on the calculations.
        """
        best_move = None
        best_score = float('-inf') #Best_score is initialised with negative infinity, so the first move is always better than the ones after.

        for move in moves:
            total_score = 0
            for _ in range(self.num_samples):
                simulated_gamestate = self.simulate_move(gamestate, leader_move) #Simulates state after leader's move.
                simulated_gamestate = self.simulate_move(simulated_gamestate, move) #Simulates state after follower's move.

                score = self.calculate_score(simulated_gamestate)

                if self.is_marriage_high_reward(simulated_gamestate, move):
                    score += 20  #Regular marriage will add 20 points to the score

                if isinstance(move, RegularMove):
                    score += self.calculated_points_card(move.card)

                opponent_potential = self.estimate_opponents_potential_score(perspective)
                total_score += score - opponent_potential

            average_score = total_score / self.num_samples
            if average_score > best_score: #Compare if average_score is greater than best_score and if so continue.
                best_score = average_score #Adjust value of best_score.
                best_move = move #Adjust score of best_move.

        return best_move

    def __evaluate_points_accumulated(self, gamestate: GameState, move: Move) -> int:
        """
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

        unknown_cards_count = len(perspective.get_opponent_hand_in_phase_two()) - len(perspective.get_known_cards_of_opponent_hand())
        average_value_card = self.get_average_value_card(perspective) #Calculates average of the cards in opponents hand.
        estimated_score += unknown_cards_count * average_value_card #Adds estimated points from the unknown cards from the opponent to estimated_score.

        estimated_score += self.estimate_marriage_points(perspective)

        return estimated_score
    
    def get_average_value_card(self, perspective: PlayerPerspective) -> float:
        """
        Calculate the average value of the remaining cards in the deck.
        Returns the average point value of unseen cards.
        """
        scorer = SchnapsenTrickScorer()
        unseen_cards = perspective.get_engine().deck_generator.get_initial_deck() - perspective.seen_cards(None) #Calculates set of unseen cards by substracting unseen cards from intial deck.
        total_points = sum(scorer.rank_to_points(card.rank) for card in unseen_cards) #Calculates total_points of unseen cards by summing up the values of each unseen cards.
        return total_points / len(unseen_cards) if unseen_cards else 0

    def estimate_marriage_points(self, perspective: PlayerPerspective) -> int:
        """
        Estimate points the opponent might gain from marriages.
        Returns estimated points from potential marriages.
        """
        estimated_marriage_points = 0
        scorer = SchnapsenTrickScorer()

        potential_marriages = {suit: False for suit in Suit} #Creates a dictionary with suits as key and false as their values, to see which suits are left as potential marriages.

        for card in perspective.get_opponent_won_cards(): #Looks through opponent's cards which they won.
            if card.rank in [Rank.QUEEN, Rank.KING]: #Checks the rank of the cards whether they are a King or Queen.
                potential_marriages[card.suit] = True #Sets the value of said suit to True in the dictionary.

        for suit, potential in potential_marriages.items():
            if potential:
                estimated_marriage_points += scorer.marriage(Marriage(Card(Rank.QUEEN, suit), Card(Rank.KING, suit)), perspective.get_state_in_phase_two()).pending_points * 0.5 #Estimates potential points that opponent can gain from a potential marriage involving the current suit by scoring marriage and multiplying the pending points by 0.5.

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
            higher_cards = [card for card in opponent_hand if card.rank > move.card.rank] #Gets list of card in opponent's hand that are higher than the rank of the card in 'move'.
            return len(higher_cards) / len(opponent_hand) if opponent_hand else 0 #Returns probability of being beaten by opponent based on the cards in 'move'.

        elif isinstance(move, Marriage):
            same_suit_cards = [card for card in opponent_hand if card.suit == move.suit and card.rank > Rank.QUEEN] #Creates a list of the cards in the opponent's hand with the same suit as the card in 'move' and a higher rank than Queen.
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