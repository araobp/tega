import tega.tree
import tega.driver

import math
import random
import datetime

MAXI = 10
MAXJ = 10
MAXK = 10
RAND_RANGE = 10000

if __name__ == '__main__':

    range_ = MAXI * MAXJ * MAXK
    now = datetime.datetime.now

    d = tega.driver.Driver()
    
    print('### PUT performance ###')

    start = now()
    print(start)
    r = tega.tree.Cont('r')
    for i in range(0, MAXI):
        for j in range(0,MAXJ):
            d.begin()
            for k in range(0,MAXK):
                r[str(i)][str(j)][str(k)] = random.randrange(RAND_RANGE)
                d.put(r[str(i)][str(j)][str(k)])
            d.commit()
    finish = now()
    print(finish)
    delta = (finish - start).total_seconds()
    print('Elapsed time: {} sec'.format(delta))
    print('Throughput: {} puts/sec'.format(math.floor(range_/delta)))

    print('')

    print('### GET performance ###')

    start = now()
    print(start)
    for i in range(0, MAXI):
        for j in range(0,MAXJ):
            for k in range(0,MAXK):
                d.get(path='r.{}.{}.{}'.format(i,j,k))
    finish = now()
    print(finish)
    delta = (finish - start).total_seconds()
    print('Elapsed time: {} sec'.format(delta))
    print('Throughput: {} gets/sec'.format(math.floor(range_/delta)))
