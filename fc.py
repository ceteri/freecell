#!/usr/bin/env python
# encoding: utf-8

import collections
import operator
import sys


Card = collections.namedtuple('Card', ['suit', 'rank'])
Card.RANK_STR = "A23456789TJQK"
Card.SUIT_STR = "CDHS"

def repr_card(card):
  return Card.RANK_STR[card.rank] + Card.SUIT_STR[card.suit]

def can_stack(card, under):
  if (card.rank - under.rank) != 1:
      return False
  elif under.suit in [0, 3] and card.suit not in [1, 2]:
      return False
  elif under.suit in [1, 2] and card.suit not in [0, 3]:
      return False
  else:
      return True

def parse_card(str):
  rank, suit = list(str)
  r = Card.RANK_STR.index(rank)
  s = Card.SUIT_STR.index(suit)
  return Card(s, r)

Card.__repr__ = repr_card
Card.can_stack = can_stack
Card.parse_card = parse_card


class Stack:
  def __init__(self):
    self.__items = []

  def __len__(self):
    return len(self.__items)

  def get_items(self):
    return self.__items

  def is_empty(self):
    return len(self.__items) == 0

  def push(self, item):
    self.__items.append(item)

  def pop(self):
    return self.__items.pop()

  def peek(self):
    return self.__items[-1] if len(self.__items) > 0 else None


class Link:
  ## http://stackoverflow.com/questions/15710895/doubly-linked-list-iterator-python

  def __init__(self, item, prev=None, next=None):
    self.item = item
    self.prev = prev
    self.next = next

  def __iter__(self):
    here = self

    while here:
      yield here.item
      here = here.next

  def __reversed__(self):
    here = self

    while here:
      yield here.item
      here = here.prev


class Position:
  def __init__(self, card, where, index, depth=0):
    self.card = card
    self.where = where
    self.index = index
    self.depth = depth
    self.weight = 0

  def __repr__(self):
    return "%s: %s %d %d - %d" % (self.card, self.where, self.index, self.depth, self.weight)


class Game:
  # https://en.wikipedia.org/wiki/FreeCell
  DEFAULT_SEED = 11982

  N_CARDS = 52
  N_SUITS = 4
  N_RANKS = 12
  N_OPEN = 4
  N_CASCADES = 8

  WHERE_FOUNDATION = "F"
  WHERE_OPEN = "O"
  WHERE_CASCADE = "C"

  # game generator based on:
  # https://rosettacode.org/wiki/Deal_cards_for_FreeCell#Python

  @staticmethod
  def random_generator(seed=1):
    max_int32 = (1 << 31) - 1
    seed = seed & max_int32
 
    while True:
      seed = (seed * 214013 + 2531011) & max_int32
      yield seed >> 16


  def reset(self, seed):
    self.seed = seed
    self.moves = []
    self.open = Stack()
    self.fond = [Stack() for i in xrange(self.N_SUITS)]

    # generate the deck, i.e., "shuffle"

    deck = range(self.N_CARDS - 1, -1, -1)
    rnd = self.random_generator(seed)

    for i, r in zip(range(self.N_CARDS), rnd):
      j = (self.N_CARDS - 1) - r % (self.N_CARDS - i)
      deck[i], deck[j] = deck[j], deck[i]

    cards = [Card(c % self.N_SUITS, c / self.N_SUITS) for c in deck]

    # deal the deck across the cascades

    self.layout = {}
    self.cascades = [Stack() for s in xrange(self.N_CASCADES)]

    for i in xrange(len(cards)):
      card = cards[i]
      s = i % self.N_CASCADES
      self.cascades[s].push(card)

      depth = len(self.cascades[s].get_items()) - 1
      position = Position(card, self.WHERE_CASCADE, s, depth)
      self.layout[repr(card)] = Link(position)

    # link the cards as a graph
      
    self.fond_head = [None for i in xrange(self.N_SUITS)]
    self.fond_tail = [None for i in xrange(self.N_SUITS)]

    for key in sorted(self.layout, key=operator.itemgetter(1)):
      link = self.layout[key]
      card = link.item.card

      if not self.fond_head[card.suit]:
        # first instance of this suit
        self.fond_head[card.suit] = link
        self.fond_tail[card.suit] = link
      else:
        self.fond_tail[card.suit].next = link
        link.prev = self.fond_tail[card.suit]
        self.fond_tail[card.suit] = link


  def __init__(self, seed):
    self.reset(seed)

    # (temp) show the initial layout
    for suit in xrange(self.N_SUITS):
      for position in reversed(self.fond_tail[suit]):
        print position


  def render(self):
    print
    print "hand %d step %d" % (self.seed, len(self.moves))
    print "open:", " ".join([ repr(c) for c in self.open.get_items()])
    print "done:", [ f.peek() for f in self.fond ]
    print "moves:", "; ".join(self.moves)
    print

    todo = sum([len(s.get_items()) for s in self.cascades])
    depth = 0

    while todo > 0:
      row = []

      for s in self.cascades:
        items = s.get_items()

        if len(items) > depth:
          row.append(repr(items[depth]))
          todo -= 1
        else:
          row.append("  ")

      print " ".join(row)
      depth += 1

    print


  def test_win(self, verbose=False):
    """is the game won at this point?"""
    quick_win = True

    for s in self.cascades:
      items = s.get_items()
      last_rank = self.N_RANKS
      g_list = []

      for card in items:
        gradient = last_rank - card.rank
        g_list.append(" ".join([repr(card), str(gradient)]))
        last_rank = card.rank

        if gradient < 0:
          quick_win = False

      if verbose:
        print " | ".join([g for g in g_list])

    return quick_win


  def play_foundation(self, move, card_name):
    position = self.layout[card_name]
    card = position.item

    print "play %s in FOUNDATION" % (card)


  def move_open_cell(self, move, card_name):
    position = self.layout[card_name].item
    card = position.card

    if len(self.open) <= self.N_OPEN:
      if position.where == self.WHERE_CASCADE:
        cascade = self.cascades[position.index]

        if cascade.peek() == card:
          print "move %s to OPEN CELL" % (position)
          cascade.pop()

          self.open.push(card)
          position.where = self.WHERE_OPEN
          position.index = 0
          position.depth = 0
          position.weight = 0

          self.moves.append(move)
        else:
          print "CARD NOT PLAYABLE"
      else:
        print "ILLEGAL MOVE"
    else:
      print "NO OPEN CELLS"


  def build_cascade(self, move, card_name, dest_index):
    position = self.layout[card_name]
    card = position.item

    print "build %s on CASCADE %d" % (card, dest_index)


  @staticmethod
  def quit_loop():
    print "bye."
    sys.exit(0)


  @staticmethod
  def show_error(line):
    print "incomprehsible garble...%s\n" % (line)


  def replay_moves(self, log_moves):
    """replay a log of the moves, line by line"""
    for log_line in log_moves.split(";"):
      self.one_line(log_line)


  def one_line(self, raw_line):
    """run one line of input"""
    try:
      line = raw_line.strip().upper().split(" ")
      move = " ".join(line)

      if "QUIT".startswith(line[0]):
        self.quit_loop()
      elif "REPLAY".startswith(line[0]):
        log_moves = " ".join(line[1:])
        self.replay_moves(log_moves)
      else:
        card_name = line[0]
        dest_where = line[1]

        if not card_name in self.layout:
          self.show_error(line)

        elif "FOUNDATION".startswith(dest_where):
          self.play_foundation(move, card_name)

        elif "OPEN".startswith(dest_where):
          self.move_open_cell(move, card_name)

        elif "CASCADE".startswith(dest_where):
          dest_index = int(line[2])
          self.build_cascade(move, card_name, dest_index)

        else:
          print "huh?"

    except IndexError:
      self.show_error(line)
    except KeyError:
      self.show_error(line)


  def repl(self):
    while True:
      self.render()

      if self.test_win(True):
        print "#WINNING"
        self.quit_loop()

      try:
        line = raw_input("\n? ")
        self.one_line(line)
      except EOFError:
        self.quit_loop()


if __name__ == '__main__':
  seed = int(sys.argv[1]) if len(sys.argv) == 2 else Game.DEFAULT_SEED
  game = Game(seed)
  game.repl()
