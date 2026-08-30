import re, collections

def get_stats(vocab): # vocab:字典
    """统计词元对频率"""
    # 第一次合并
    pairs = collections.defaultdict(int) # 创建一个默认字典(键值对)，默认值为0
    # 第一次：word:'h u g </w>' freq:1
    # 第二次：word:'p u g </w>' freq:1
    # 第三次：word:'p u n </w>' freq:1
    # 第四次：word:'b u n </w>' freq:1
    for word, freq in vocab.items(): 
        # 第一次：symbols:['h', 'u', 'g', '</w>']
        # 第二次：symbols:['p', 'u', 'g', '</w>']
        # 第三次：symbols:['p', 'u', 'n', '</w>']
        # 第四次：symbols:['b', 'u', 'n', '</w>']
        symbols = word.split() 
        for i in range(len(symbols)-1):
            # 第一次：symbols[i]:h, symbols[i+1]:u  pairs['h u']:1
            #        symbols[i]:u, symbols[i+1]:g  pairs['u g']:1
            #        symbols[i]:g, symbols[i+1]:</w>  pairs['g </w>']:1
            # 第二次：symbols[i]:p, symbols[i+1]:u  pairs['p u']:1
            #        symbols[i]:u, symbols[i+1]:g  pairs['u g']:2
            #        symbols[i]:g, symbols[i+1]:</w>  pairs['g </w>']:2
            # 第三次：symbols[i]:p, symbols[i+1]:u  pairs['p u']:1
            #        symbols[i]:u, symbols[i+1]:n  pairs['u n']:1
            #        symbols[i]:n, symbols[i+1]:</w>  pairs['n </w>']:1
            # 第四次：symbols[i]:b, symbols[i+1]:u  pairs['b u']:1
            #        symbols[i]:u, symbols[i+1]:n  pairs['u n']:2
            #        symbols[i]:n, symbols[i+1]:</w>  pairs['n </w>']:2
            pairs[symbols[i],symbols[i+1]] += freq
    return pairs

def merge_vocab(pair, v_in):
    """合并词元对"""
    #
    v_out = {}
    # 第一次：pair:'u g'
    bigram = re.escape(' '.join(pair)) # 将字符对用空格连接成字符串
    p = re.compile(r'(?<!\S)' + bigram + r'(?!\S)')
    # 第一次：word:'h u g </w>'
    for word in v_in:
        # 第一次：w_out:'h ug </w>'
        # 第二次：w_out:'p ug </w>'
        # 第三次：w_out:'p u n </w>'
        # 第四次：w_out:'b u n </w>'
        w_out = p.sub(''.join(pair), word) # 替换字符对,将h u g替换为h ug </w>
        # 第一次：v_out={'h ug </w>':1}
        # 第二次：v_out={'p ug </w>':1}
        # 第三次：v_out={'p u n </w>':1}
        # 第四次：v_out={'b u n </w>':1}
        v_out[w_out] = v_in[word]
    return v_out

# 准备语料库，每个词末尾加上</w>表示结束，并切分好字符
vocab = {'h u g </w>': 1, 'p u g </w>': 1, 'p u n </w>': 1, 'b u n </w>': 1}
num_merges = 4 # 设置合并次数

for i in range(num_merges):
    pairs = get_stats(vocab)
    if not pairs:
        break
    # 第一次：best:'u g'
    best = max(pairs, key=pairs.get)

    vocab = merge_vocab(best, vocab)
    print(f"第{i+1}次合并: {best} -> {''.join(best)}")
    print(f"新词表（部分）: {list(vocab.keys())}")
    print("-" * 20)