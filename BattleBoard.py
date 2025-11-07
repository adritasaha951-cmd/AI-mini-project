#!/usr/bin/env python3
import tkinter as tk
from copy import deepcopy
import threading
from tkinter import messagebox

# ---------------- Constants ----------------
BOARD_SIZE = 8
SQUARE_SIZE = 80
WHITE_COLOR = '#F0D9B5'
BLACK_COLOR = '#B58863'
HIGHLIGHT_COLOR = '#A9D18E'
LEGAL_MOVE_COLOR = '#FFEB3B'
BORDER_COLOR = 'black'

UNICODE_PIECES = {
    'K': '\u2654', 'Q': '\u2655', 'R': '\u2656', 'B': '\u2657', 'N': '\u2658', 'P': '\u2659',
    'k': '\u265A', 'q': '\u265B', 'r': '\u265C', 'b': '\u265D', 'n': '\u265E', 'p': '\u265F'
}

PIECE_VALUES = {'K': 20000, 'Q': 900, 'R': 500, 'B': 330, 'N': 320, 'P': 100,
                'k': -20000, 'q': -900, 'r': -500, 'b': -330, 'n': -320, 'p': -100}

# ---------------- Game State ----------------
class GameState:
    def __init__(self):
        self.board = self.create_start_board()
        self.white_to_move = True
        self.move_history = []
        self.captured_white = []
        self.captured_black = []

    def create_start_board(self):
        return [
            ['r','n','b','q','k','b','n','r'],
            ['p','p','p','p','p','p','p','p'],
            ['.','.','.','.','.','.','.','.'],
            ['.','.','.','.','.','.','.','.'],
            ['.','.','.','.','.','.','.','.'],
            ['.','.','.','.','.','.','.','.'],
            ['P','P','P','P','P','P','P','P'],
            ['R','N','B','Q','K','B','N','R']
        ]

    def in_bounds(self,r,c): return 0<=r<8 and 0<=c<8
    def get_piece(self,r,c): return self.board[r][c]
    def set_piece(self,r,c,piece): self.board[r][c] = piece

    def make_move(self,move):
        (r1,c1),(r2,c2),prom = move
        piece = self.get_piece(r1,c1)
        captured = self.get_piece(r2,c2)
        self.set_piece(r2,c2,piece)
        self.set_piece(r1,c1,'.')
        if captured != '.':
            if captured.isupper(): self.captured_white.append(captured)
            else: self.captured_black.append(captured)
        if prom: self.set_piece(r2,c2,'Q' if piece.isupper() else 'q')
        self.white_to_move = not self.white_to_move
        self.move_history.append((move,captured))

    def undo_move(self):
        if not self.move_history: return
        (r1c1,r2c2,prom),captured = self.move_history.pop()
        (r1,c1),(r2,c2),_ = r1c1,r2c2,prom
        piece = self.get_piece(r2,c2)
        if prom: piece = 'P' if piece.isupper() else 'p'
        self.set_piece(r1,c1,piece)
        self.set_piece(r2,c2,captured)
        if captured != '.':
            if captured.isupper(): self.captured_white.pop()
            else: self.captured_black.pop()
        self.white_to_move = not self.white_to_move

    def copy(self):
        gs = GameState()
        gs.board = deepcopy(self.board)
        gs.white_to_move = self.white_to_move
        gs.move_history = deepcopy(self.move_history)
        gs.captured_white = deepcopy(self.captured_white)
        gs.captured_black = deepcopy(self.captured_black)
        return gs

    def is_game_over(self):
        white_king = any('K' in row for row in self.board)
        black_king = any('k' in row for row in self.board)
        if not white_king: return True,'Black wins!'
        elif not black_king: return True,'White wins!'
        return False,''

# ---------------- Evaluation ----------------
def evaluate_board(gs):
    score=0
    for r in range(8):
        for c in range(8):
            p=gs.board[r][c]
            if p!='.': score+=PIECE_VALUES.get(p,0)
    return score

# ---------------- Move Generation ----------------
def generate_all_moves(gs):
    moves=[]
    for r in range(8):
        for c in range(8):
            piece = gs.get_piece(r,c)
            if piece=='.': continue
            moves.extend(generate_piece_moves(gs,r,c,piece))
    return moves

def generate_piece_moves(gs,r,c,piece):
    moves=[]
    directions=[]
    enemy = lambda p: p!='.' and p.isupper()!=piece.isupper()

    if piece.upper()=='P':
        dir = -1 if piece.isupper() else 1
        start = 6 if piece.isupper() else 1
        if gs.in_bounds(r+dir,c) and gs.get_piece(r+dir,c)=='.':
            prom = (r+dir==0 or r+dir==7)
            moves.append(((r,c),(r+dir,c),prom))
            if r==start and gs.get_piece(r+2*dir,c)=='.': moves.append(((r,c),(r+2*dir,c),False))
        for dc in [-1,1]:
            if gs.in_bounds(r+dir,c+dc):
                target=gs.get_piece(r+dir,c+dc)
                if enemy(target):
                    prom=(r+dir==0 or r+dir==7)
                    moves.append(((r,c),(r+dir,c+dc),prom))
    elif piece.upper()=='N':
        for dr,dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nr,nc=r+dr,c+dc
            if gs.in_bounds(nr,nc):
                target=gs.get_piece(nr,nc)
                if target=='.' or enemy(target): moves.append(((r,c),(nr,nc),False))
    elif piece.upper()=='B': directions=[(-1,-1),(-1,1),(1,-1),(1,1)]
    elif piece.upper()=='R': directions=[(-1,0),(1,0),(0,-1),(0,1)]
    elif piece.upper()=='Q': directions=[(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)]
    elif piece.upper()=='K':
        for dr in [-1,0,1]:
            for dc in [-1,0,1]:
                if dr==0 and dc==0: continue
                nr,nc=r+dr,c+dc
                if gs.in_bounds(nr,nc):
                    target=gs.get_piece(nr,nc)
                    if target=='.' or enemy(target): moves.append(((r,c),(nr,nc),False))
    if directions:
        for dr,dc in directions:
            nr,nc=r+dr,c+dc
            while gs.in_bounds(nr,nc):
                target=gs.get_piece(nr,nc)
                if target=='.': moves.append(((r,c),(nr,nc),False))
                elif enemy(target): moves.append(((r,c),(nr,nc),False)); break
                else: break
                nr+=dr
                nc+=dc
    return moves

# ---------------- Minimax ----------------
def minimax_alpha_beta(gs,depth,alpha,beta,maximizing):
    if depth==0: return evaluate_board(gs),None
    moves=generate_all_moves(gs)
    if not moves: return evaluate_board(gs),None
    best_move=None
    if maximizing:
        max_eval=float('-inf')
        for move in moves:
            gs.make_move(move)
            val,_=minimax_alpha_beta(gs,depth-1,alpha,beta,False)
            gs.undo_move()
            if val>max_eval: max_eval=val; best_move=move
            alpha=max(alpha,val)
            if beta<=alpha: break
        return max_eval,best_move
    else:
        min_eval=float('inf')
        for move in moves:
            gs.make_move(move)
            val,_=minimax_alpha_beta(gs,depth-1,alpha,beta,True)
            gs.undo_move()
            if val<min_eval: min_eval=val; best_move=move
            beta=min(beta,val)
            if beta<=alpha: break
        return min_eval,best_move

# ---------------- GUI ----------------
class ChessGUI:
    def __init__(self,root):
        self.root=root
        root.title("BattleBoard")
        self.gs=GameState()
        self.selected=None
        self.legal_moves=[]
        self.ai_depth=2
        self.ai_thinking=False

        # Frames
        self.ctrl_frame=tk.Frame(root)
        self.ctrl_frame.pack(side='left', padx=10, pady=10, anchor='n')
        self.board_frame=tk.Frame(root, bg=BORDER_COLOR)
        self.board_frame.pack(side='right', padx=10, pady=10)

        # Canvas
        self.canvas=tk.Canvas(self.board_frame,width=BOARD_SIZE*SQUARE_SIZE,height=BOARD_SIZE*SQUARE_SIZE,bg=BORDER_COLOR)
        self.canvas.pack(padx=2,pady=2)
        self.canvas.bind('<Button-1>',self.on_click)

        # Controls
        tk.Button(self.ctrl_frame,text='New Game',command=self.new_game,width=20,bg='#4CAF50',fg='white',font=('Arial',12,'bold')).pack(pady=5)
        tk.Button(self.ctrl_frame,text='Undo',command=self.undo,width=20,bg='#f44336',fg='white',font=('Arial',12,'bold')).pack(pady=5)
        tk.Label(self.ctrl_frame,text='AI Depth:',font=('Arial',12)).pack(pady=5)
        self.depth_entry=tk.Spinbox(self.ctrl_frame,from_=1,to=4,width=5,font=('Arial',12))
        self.depth_entry.pack(pady=5)
        self.status=tk.Label(self.ctrl_frame,text='White to move',font=('Arial',14,'bold'))
        self.status.pack(pady=10)
        tk.Label(self.ctrl_frame,text='Captured White:',font=('Arial',12,'bold')).pack(pady=5)
        self.captured_white_label=tk.Label(self.ctrl_frame,text='',font=('Arial',12))
        self.captured_white_label.pack(pady=5)
        tk.Label(self.ctrl_frame,text='Captured Black:',font=('Arial',12,'bold')).pack(pady=5)
        self.captured_black_label=tk.Label(self.ctrl_frame,text='',font=('Arial',12))
        self.captured_black_label.pack(pady=5)
        self.score_label=tk.Label(self.ctrl_frame,text='Score: 0',font=('Arial',12,'bold'))
        self.score_label.pack(pady=10)

        self.draw_board()

    def draw_board(self):
        self.canvas.delete('all')
        for r in range(8):
            for c in range(8):
                x1,y1=c*SQUARE_SIZE,r*SQUARE_SIZE
                x2,y2=x1+SQUARE_SIZE,y1+SQUARE_SIZE
                color=WHITE_COLOR if (r+c)%2==0 else BLACK_COLOR
                self.canvas.create_rectangle(x1,y1,x2,y2,fill=color,outline='black')
        if self.selected:
            r,c=self.selected
            self.canvas.create_rectangle(c*SQUARE_SIZE,r*SQUARE_SIZE,(c+1)*SQUARE_SIZE,(r+1)*SQUARE_SIZE,fill=HIGHLIGHT_COLOR)
            for move in self.legal_moves:
                if move[0]==self.selected:
                    r2,c2=move[1]
                    self.canvas.create_rectangle(c2*SQUARE_SIZE,r2*SQUARE_SIZE,(c2+1)*SQUARE_SIZE,(r2+1)*SQUARE_SIZE,fill=LEGAL_MOVE_COLOR)
        for r in range(8):
            for c in range(8):
                p=self.gs.get_piece(r,c)
                if p!='.':
                    x=c*SQUARE_SIZE+SQUARE_SIZE/2
                    y=r*SQUARE_SIZE+SQUARE_SIZE/2
                    color='black' if p.isupper() else 'white'
                    self.canvas.create_text(x,y,text=UNICODE_PIECES[p],font=('Segoe UI Symbol',36),fill=color)
        self.update_status()

    def on_click(self,event):
        if self.ai_thinking: return
        c,r=event.x//SQUARE_SIZE,event.y//SQUARE_SIZE
        if not self.gs.in_bounds(r,c): return
        piece=self.gs.get_piece(r,c)
        if self.selected:
            legal=[m for m in self.legal_moves if m[0]==self.selected and m[1]==(r,c)]
            if legal:
                self.gs.make_move(legal[0])
                self.selected=None
                self.legal_moves=[]
                self.draw_board()
                threading.Thread(target=self.ai_move).start()
            else:
                self.selected=None
                self.legal_moves=[]
                self.draw_board()
        else:
            if piece!='.' and piece.isupper()==self.gs.white_to_move:
                self.selected=(r,c)
                self.legal_moves=generate_all_moves(self.gs)
                self.draw_board()

    def ai_move(self):
        self.ai_thinking=True
        self.ai_depth=int(self.depth_entry.get())
        _,move=minimax_alpha_beta(self.gs,self.ai_depth,float('-inf'),float('inf'),False)
        if move: self.gs.make_move(move)
        self.selected=None
        self.legal_moves=[]
        self.draw_board()
        self.ai_thinking=False

    def new_game(self):
        self.gs=GameState()
        self.selected=None
        self.legal_moves=[]
        self.draw_board()

    def undo(self):
        self.gs.undo_move()
        self.draw_board()

    def update_status(self):
        side='White' if self.gs.white_to_move else 'Black'
        self.status.config(text=f'{side} to move')
        self.captured_white_label.config(text=' '.join([UNICODE_PIECES[p] for p in self.gs.captured_white]))
        self.captured_black_label.config(text=' '.join([UNICODE_PIECES[p] for p in self.gs.captured_black]))
        score = evaluate_board(self.gs)
        self.score_label.config(text=f'Score: {score}')
        over,msg=self.gs.is_game_over()
        if over: messagebox.showinfo('Game Over',msg)

# ---------------- Run ----------------
if __name__=='__main__':
    root=tk.Tk()
    gui=ChessGUI(root)
    root.mainloop()
