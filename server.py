import sys, os
sys.path.append('tornado')
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import tornado.template
import traceback
from itertools import cycle

loader = tornado.template.Loader(os.path.join(os.path.join(os.path.realpath(__file__) + '/../'), 'templates'))

class Game(object):
    def __init__(self):
        self.players = []
        self.state = self.add_player
        self.winner = None

    def add_player(self, player):
        self.players.append(player)
        if len(self.players) == 2:
            self.start_game()

    def start_game(self):
        self.grid = [[None, None, None],
                     [None, None, None],
                     [None, None, None]]
        # This creates a generator which cycles over the elements in a list
        self.turn_order = cycle(self.players)
        self.next_player = self.turn_order.next()
        self.winner = None
        self.broadcast(None, 'MSG: New game')

    def broadcast(self, sender, message):
        ''' broadcast will send a message to all players except the sender.
            Using None as the sender will broadcast to all players'''
        try:
            if sender and sender != self.next_player:
                sender.socket.write_message('ERR: Out of turn!')
                return
            if message.startswith('MOVE:'):
                _, x, y = message.split(':')
                if self.grid[int(x)][int(y)] != None:
                    sender.socket.write_message('ERR: Space occupied')
                    return
                self.grid[int(x)][int(y)] = sender.symbol
                self.check_winner()
                self.next_player = self.turn_order.next()
            for player in self.players:
                if player == sender:
                    player.socket.write_message('UPDATE')
                if player != sender:
                    player.socket.write_message(message)
        except:
            traceback.print_exc()
    
    def check_winner(self):
        def all_same(symbol, set):
            set = map(lambda _: _ == symbol, set)
            return all(set)

        for player in self.players:
            for y in xrange(0, 3):
                if all_same(player.symbol, self.grid[y]):
                    self.winner = player.symbol
            for x in xrange(0, 3):
                if all_same(player.symbol, [self.grid[0][x],
                                            self.grid[1][x],
                                            self.grid[2][x]]):
                    self.winner = player.symbol
            if all_same(player.symbol, [self.grid[0][0],
                                        self.grid[1][1],
                                        self.grid[2][2]]):
                    self.winner = player.symbol
            if all_same(player.symbol, [self.grid[0][2],
                                        self.grid[1][1],
                                        self.grid[2][0]]):
                    self.winner = player.symbol
        if self.winner:
            self.broadcast(None, 'WIN: ' + self.winner)
            self.start_game()

class Player(object):
    def __init__(self, symbol, game):
        self.symbol = symbol
        self.socket = None
        self.game = game
        self.game.add_player(self)

class PlayerHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        self.player = kwargs.pop('player')
        self.template = kwargs.pop('template')
        super(PlayerHandler, self).__init__(*args, **kwargs)

    def get(self):
        self.write(loader.load(self.template).generate(player=self.player))

class PlayerWebSocket(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        self.player = kwargs.pop('player')
        self.player.socket = self
        super(PlayerWebSocket, self).__init__(*args, **kwargs)

    def open(self):
        self.receive_message(self.on_message)
    
    def on_message(self, message):
        self.player.game.broadcast(self.player, message)
        # Keep receiving messages
        self.receive_message(self.on_message)

game = Game()
playerX = Player('X', game)
playerO = Player('O', game)

settings = {'static_path': os.path.join(os.path.realpath(__file__ + '/../'), 'web-socket-js')}

application = tornado.web.Application(
    [(r'/X',      PlayerHandler,   {'player': playerX,
                                    'template': 'player.html'}),
     (r'/X/grid', PlayerHandler,   {'player': playerX,
                                    'template': 'grid.html'}),
     (r'/X/ws',   PlayerWebSocket, {'player': playerX}),
     (r'/O',      PlayerHandler,   {'player': playerO,
                                    'template': 'player.html'}),
     (r'/O/grid', PlayerHandler,   {'player': playerO,
                                    'template': 'grid.html'}),
     (r'/O/ws',   PlayerWebSocket, {'player': playerO})],
    **settings)

if __name__ == '__main__':
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(9999)
    tornado.ioloop.IOLoop.instance().start()
