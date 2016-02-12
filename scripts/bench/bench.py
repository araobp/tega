import tega.tree
import tega.driver

import random

MAXI = 10
MAXJ = 10
MAXK = 10

if __name__ == '__main__':
    r = tega.tree.Cont('r')
    d = tega.driver.Driver()
    for i in range(0, MAXI):
        for j in range(0,MAXJ):
            for k in range(0,MAXK):
                r[str(i)][str(j)][str(k)] = random.randrange(1000)
                d.put(r[str(i)][str(j)][str(k)])
