" Turn off Vi compatible
set nocompatible

" Enable intelligent auto-indenting for filetypes
filetype indent plugin on
" Enable syntax highlighting
syntax on

" ================ Vundle Settings ===================
" Set runtime path to include Vundle & initialize
set rtp+=~/.vim/bundle/Vundle.vim

call vundle#begin()

Plugin 'VundleVim/Vundle.vim'       " Let Vundle manage Vundle. REQUIRED!

" Plugins
Plugin 'Valloric/YouCompleteMe'     " Awesome auto-complete
Plugin 'scrooloose/nerdtree'        " Tree explorer
Plugin 'sheerun/vim-polyglot'       " Language packs syntax supports
Plugin 'amadeus/vim-mjml'           " mjml syntax support
call vundle#end()

" ================ General Settings ==================
" 
set number                          " Enable line numbers
set relativenumber                  " Enable relative numbers
set backspace=indent,eol,start 	    " Allows backspacing
set history=1000	       	        " Lots & lots of history
set showcmd		       	            " Show partial commands
set showmode		       	        " Show current mode
set visualbell		       	        " Use visual bell instead of beeping sound
set autoread		       	        " Reload files changes outside of vim
set showmatch		       	        " Briefly jump to matching bracket
set wildmenu		       	        " Visual autocomplete for command menu
set nowrap			                " Don't wrap lines
set linebreak			            " Wrap lines at convenient points
set cursorline			            " Highlight current line

" ================ Search Settings  ==================
"
set incsearch			            " Find next match when searching
set hlsearch			            " Highlight search by default
set ignorecase			            " case insensitive search
set smartcase			            " except when using capital letters

" ================ Indentation Settings ==============
"
set autoindent			            " Enable autoindenting
set smartindent			            " Enable smartindenting
set smarttab			            " Insert tabs on start of a line
set shiftwidth=4		            " Use 4 spaces for autoindenting
set softtabstop=4		            "
set tabstop=4			            "
set expandtab			            " Each indentation is 4 spaces. NO TABS!
set list listchars=tab:\ \ ,trail:· " Display tabs & spaces visually

" ================ Folding Settings ==================
"
set foldmethod=indent		        " Fold based on indentation
set foldnestmax=3		            " Set max fold nesting
set nofoldenable		            " Disable fold by default

" ================ Backup Settings ===================
"
set noswapfile                       " No swap files
set nobackup                        " No backup
set nowb                            " No backup while editing

" ================ Plugin Settings ===================
"
autocmd StdinReadPre * let s:std_in=1
autocmd VimEnter * if argc() == 0 && !exists("s:std_in") | NERDTree | endif
