import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
from functions import gilbert

_STATES = {
    'Bell': (
        np.array([[1/2., 0, 0, 1/2.],
                  [0,    0, 0, 0   ],
                  [0,    0, 0, 0   ],
                  [1/2., 0, 0, 1/2.]]),
        [2, 2],
    ),
    'GHZ': (
        np.array([[0.5, 0, 0, 0, 0, 0, 0, 0.5],
                  [0,   0, 0, 0, 0, 0, 0, 0  ],
                  [0,   0, 0, 0, 0, 0, 0, 0  ],
                  [0,   0, 0, 0, 0, 0, 0, 0  ],
                  [0,   0, 0, 0, 0, 0, 0, 0  ],
                  [0,   0, 0, 0, 0, 0, 0, 0  ],
                  [0,   0, 0, 0, 0, 0, 0, 0  ],
                  [0.5, 0, 0, 0, 0, 0, 0, 0.5]]),
        [2, 2, 2],
    ),
    'W': (
        np.array([[0, 0,     0,     0, 0,     0, 0, 0],
                  [0, 1/3.,  1/3.,  0, 1/3.,  0, 0, 0],
                  [0, 1/3.,  1/3.,  0, 1/3.,  0, 0, 0],
                  [0, 0,     0,     0, 0,      0, 0, 0],
                  [0, 1/3.,  1/3.,  0, 1/3.,  0, 0, 0],
                  [0, 0,     0,     0, 0,      0, 0, 0],
                  [0, 0,     0,     0, 0,      0, 0, 0],
                  [0, 0,     0,     0, 0,      0, 0, 0]]),
        [2, 2, 2],
    ),
}

def find_css_stream(state, number, trials, progress_cb):
    rho, dims = _STATES[state]
    rhoCSS, mindist, _, dist_list = gilbert(rho, dims, int(number), max_trials=int(trials), progress_cb=progress_cb)

    fig, ax = plt.subplots()
    ax.plot(dist_list, label=f"State: {state}")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Distance")
    ax.legend()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()

    matrix = [[[entry.real, entry.imag] for entry in row] for row in rhoCSS]
    return matrix, mindist, plot_url


def find_css(state, number, trials):
    rho, dims = _STATES[state]
    rhoCSS, mindist, _, dist_list = gilbert(rho, dims, int(number), max_trials=int(trials))

    fig, ax = plt.subplots()
    ax.plot(dist_list, label=f"State: {state}")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Distance")
    ax.legend()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()

    matrix = [[[entry.real, entry.imag] for entry in row] for row in rhoCSS]
    return matrix, mindist, plot_url
