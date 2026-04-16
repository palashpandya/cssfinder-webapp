import numpy as np
# from numpy import ndarray, dtype, generic, bool_
from functools import reduce
from scipy import linalg, optimize
from matplotlib import pyplot as plt

def purity(r):
    """
    Purity of the state r, calculated as Tr(r**2).
    :param r: Matrix
    :return: Real number
    """
    return np.trace(np.matmul(r, r))


def random_pure(dim):
    """
    A pure state/projector of dimension dim.
    :param dim:
    :return: Column Matrix
    """
    proj = np.transpose([np.array(np.random.normal(0, 1, dim) + complex(0, 1) * np.random.normal(0, 1, dim))])
    proj /= np.linalg.norm(proj)
    return proj


def random_pure_dl(dim_list):
    """
    Generateds a random pure state (ket) with subsystem dimensions from dim_list
    :param dim_list: List of integers
    :return: Column Matrix
    """
    ket_list = [random_pure(d) for d in dim_list]
    return reduce(np.kron, ket_list)


_BATCH_SIZE = 64

def random_pure_dl_batch(dim_list, batch_size):
    """
    Generate batch_size random product pure states.
    :param dim_list: List of subsystem dimensions
    :param batch_size: Number of states to generate
    :return: (prod(dim_list), batch_size) complex array — each column is a normalised product ket
    """
    result = (np.random.normal(0, 1, (dim_list[0], batch_size))
              + 1j * np.random.normal(0, 1, (dim_list[0], batch_size)))
    result /= np.linalg.norm(result, axis=0, keepdims=True)
    for d in dim_list[1:]:
        ket = (np.random.normal(0, 1, (d, batch_size))
               + 1j * np.random.normal(0, 1, (d, batch_size)))
        ket /= np.linalg.norm(ket, axis=0, keepdims=True)
        result = (result[:, None, :] * ket[None, :, :]).reshape(-1, batch_size)
    return result


def matrix_ejk(aj, ak, dim):
    """
    A dim x dim matrix with a 1 at index (aj,ak), and zeroes elsewhere.
    :param aj: int
    :param ak: int
    :param dim: int
    :return: Matrix
    """
    mat = np.zeros((dim, dim), complex)
    mat[aj, ak] = complex(1, 0)
    return mat


def gell_mann_basis(dim: int):
    """
    A list of (dim**2 -1) matrices that are the generators of SU(dim) Lie Algebra
    :param dim:
    :return: A list of matrices
    """
    idm = np.identity(dim, complex)
    idm /= np.linalg.norm(idm)
    # symmetric matrices in the basis:
    sym = np.zeros((int((dim * (dim - 1) / 2)), dim, dim), complex)
    idx = 0
    for k in range(dim):
        for j in range(k):
            sym[idx] = matrix_ejk(j, k, dim) + matrix_ejk(k, j, dim)
            sym[idx] /= np.linalg.norm(sym[idx])
            idx += 1
    # antisymmetric matrices in the basis
    anti_sym = np.zeros((int((dim * (dim - 1) / 2)), dim, dim), complex)
    idx = 0
    for k in range(dim):
        for j in range(k):
            anti_sym[idx] = complex(0, -1) * (matrix_ejk(j, k, dim) - matrix_ejk(k, j, dim))
            anti_sym[idx] /= np.linalg.norm(anti_sym[idx])
            idx += 1
    # diagonal matrices in the basis
    diag = np.zeros((dim - 1, dim, dim), complex)
    idx = 0
    for k in range(dim - 1):
        for j in range(k + 1):
            diag[idx] += matrix_ejk(j, j, dim)
        diag[idx] -= (k + 1) * matrix_ejk(k + 1, k + 1, dim)
        diag[idx] *= complex(np.sqrt(2 / ((k + 1) * (k + 2))), 0)
        diag[idx] /= np.linalg.norm(diag[idx])
        idx += 1
    return np.concatenate((sym, anti_sym, diag, [idm]))


def hs_distance(r1, r2):
    """
    Squared Hilbert-Schmidt distance between r1 and r2
    :param r1: Matrix
    :param r2: Matrix
    :return: distance as real number
    """
    return (np.linalg.norm(r1 - r2)).real ** 2


def pre_sel(r0, r1, r2):
    """
    Essentially gives the cosine of the angle between (r0-r1) and (r2-r1).
    Positive value indicates r2 is a good candidate, otherwise, r2 is rejected.
    This is also the value that is maximized in the function optimize_rho2 and thus to_maximize.
    :param r0:
    :param r1:
    :param r2:
    :return: float
    """
    return np.trace((r0 - r1) @ (r2 - r1)).real


def pre_sel_batch(r0, r1, kets_batch):
    """
    Vectorised pre_sel for a batch of product kets.

    For a pure state r2 = ket @ ket†:
        pre_sel = Tr((r0-r1)(r2-r1))
                = ket†(r0-r1)ket  -  Tr((r0-r1) r1)
    The constant second term is shared across the whole batch.

    :param r0: density matrix (dim, dim)
    :param r1: current CSS estimate (dim, dim)
    :param kets_batch: (dim, batch_size) array of column kets
    :return: (batch_size,) array of pre_sel values
    """
    diff = r0 - r1
    transformed = diff @ kets_batch
    return (np.einsum('ij,ij->j', kets_batch.conj(), transformed).real
            - np.trace(diff @ r1).real)

def to_maximize(x, *args):
#Old definition with more expm operations
    rho2, rho3, base_un, dim_list, lenlist, herm = args
    # herm = [np.eye(d) for d in dim_list]
    # lenlist = [len(base_un[i]) for i in range(len(base_un))]
    offset = 0
    l_base = len(base_un)
    for i in range(l_base):
        herm[i] = sum(1j * x[j + offset] * base_un[i][j] for j in range(lenlist[i]))
        herm[i] = linalg.expm(herm[i])
        offset += lenlist[i]
    unit = reduce(np.kron, herm)
    rho2u = unit @ ((rho2) @ np.transpose(np.conjugate(unit)))
    # print(unit)
    return -np.trace(rho3 @ rho2u).real

def to_maximize2(x, *args):
    # New definition with less expm operations
    rho1, rho2, rho3, base_un, dim_list, lenlist, herm = args
    # herm = [np.eye(d) for d in dim_list]
    # lenlist = [len(base_un[i]) for i in range(len(base_un))]
    offset = 0
    l_base = len(base_un)
    exponent = np.zeros((np.prod(dim_list), np.prod(dim_list)), complex)
    for i in range(l_base):
        herm[i] = sum(1j * x[j + offset] * base_un[i][j] for j in range(lenlist[i]))
        list_id = np.array([np.eye(d, dtype=complex) for d in dim_list])
        list_id[i] = herm[i]
        exponent += reduce(np.kron, list_id)
        offset += lenlist[i]
    unit = linalg.expm(exponent)
    # rho2u = unit @ np.transpose(np.conjugate(unit))

    rho2u = unit @ (rho2) @ np.transpose(np.conjugate(unit))
    # print(unit)
    return -np.trace((rho3) @ (rho2u)).real


def optimize_rho2(rho0, rho1, rho2_ket, rho2, rho3, pre1, dim_list, basis_unitary, herm):
    """
    Maximize the overlap of rho2 with the vector (rho1-rho3) using local unitary rotations on the partitions
    :param rho0:
    :param rho1:
    :param rho2_ket:
    :param rho2:
    :param rho3:
    :param pre1:
    :param dim_list:
    :param basis_unitary:
    :param herm:
    :return:
    """
    
    rho2new = rho2

    lenlist = [d * d for d in dim_list]
    x0 = np.ones(sum(lenlist))
    x_bounds = optimize.Bounds(np.full_like(x0, -10.), np.full_like(x0, 10.), False)
    res = optimize.minimize(to_maximize, x0, (rho2, rho3, basis_unitary, dim_list, lenlist, herm), method='COBYQA')
    
    xres = res.x
    offset = 0
    l_base = len(basis_unitary)
    exponent = np.zeros((np.prod(dim_list), np.prod(dim_list)), complex)
    for i in range(l_base):
        herm[i] = sum(1j * xres[j + offset] * basis_unitary[i][j] for j in range(lenlist[i]))
        list_id = np.array([np.eye(d, dtype=complex) for d in dim_list])
        list_id[i] = herm[i]
        exponent += reduce(np.kron, list_id)
        offset += lenlist[i]
    unit = linalg.expm(exponent)
    rho4 = unit @ rho2new  @ np.transpose(np.conjugate(unit))
    pre2 = pre_sel(rho0, rho1, rho4)
    # print(pre2,pre11)

    if pre2 > pre1:
        return pre2, rho4, unit @ rho2_ket
    else:
        return pre1, rho2new, rho2_ket


def gilbert(rho_in: np.array, dim_list: np.array, max_iter: int, max_trials: int, opt_state="on", rng_seed=666, rho1_in=None, progress_cb=None):
    """
    Approximate the Closest Separable State (CSS) to the given state rho_in using Gilbert's algorithm
    :param rho_in: matrix
    :param dim_list: list of subsystem dimensions (int)
    :param max_iter: max iterations/corrections
    :param max_trials: maximum trials
    :param rng_seed: seed for RNG
    :param opt_state: Optimization On/Off, default "on"
    :param rho1_in: Optional start state
    # :param file_out: output file for the list of corrections
    :return: CSS, min HS-distance, number of trials
    """

    np.random.seed(rng_seed)
    rho0 = rho_in
    #print(rho0)
    if rho1_in is None:
        rho1 = np.diag(np.diag(rho0))
    else:
        rho1 = rho1_in
    # ndim = np.multiply.reduce(dim_list)

    rho2_ket = random_pure_dl(dim_list)
    rho2 = make_density(rho2_ket)
    dist0 = hs_distance(rho0, rho1)
    trials = 1
    decrement = 0.
    basis_unitary = [gell_mann_basis(x) for x in dim_list]
    pre1 = pre_sel(rho0, rho1, rho2)
    pre2 = 0.
    itr = 1
    rho1_list = [rho1]
    dist_list = [dist0]
    rho3 = rho0 - rho1
    herm = [np.eye(d, dtype=complex) for d in dim_list]
    if opt_state.lower() == "on":
        while itr <= max_iter and trials <= max_trials:
            # if itr % 5 == 0:
            #       print(itr, dist0)

            while pre1 < 0 and trials <= max_trials:
                batch = min(_BATCH_SIZE, max_trials - trials + 1)
                kets_batch = random_pure_dl_batch(dim_list, batch)
                pre_vals = pre_sel_batch(rho0, rho1, kets_batch)
                trials += batch
                positives = np.where(pre_vals >= 0)[0]
                if len(positives) > 0:
                    best = positives[np.argmax(pre_vals[positives])]
                    rho2_ket = kets_batch[:, [best]]
                    rho2 = make_density(rho2_ket)
                    pre1 = pre_vals[best]
            if trials > max_trials:
                break

            pre1, rho2, rho2_ket = optimize_rho2(rho0, rho1, rho2_ket, rho2, rho3, pre1, dim_list, basis_unitary, herm)
            p = 1 - pre1 / hs_distance(rho1, rho2)
            dist1 = hs_distance(rho0, p * rho1 + (1 - p) * rho2)
            decrement = dist0 - dist1
            if 0 <= p <= 1 and dist1 < dist0:
                itr += 1
                rho1 = p * rho1 + (1 - p) * rho2
                rho3 = rho0 - rho1
                decrement = dist0 - dist1
                dist0 = dist1
                rho1_list.append(rho1)
                dist_list.append(dist0)
                if progress_cb:
                    progress_cb(itr, max_iter, trials, max_trials, dist0)
            if decrement < 0.0000001:
                rho2_ket = random_pure_dl(dim_list)
                rho2 = make_density(rho2_ket)
            pre1 = pre_sel(rho0, rho1, rho2)
            trials += 1
    else:
        while itr < max_iter and trials <= max_trials:
            # print(itr, dist0)

            while pre1 < 0 and trials <= max_trials:
                batch = min(_BATCH_SIZE, max_trials - trials + 1)
                kets_batch = random_pure_dl_batch(dim_list, batch)
                pre_vals = pre_sel_batch(rho0, rho1, kets_batch)
                trials += batch
                positives = np.where(pre_vals >= 0)[0]
                if len(positives) > 0:
                    best = positives[np.argmax(pre_vals[positives])]
                    rho2_ket = kets_batch[:, [best]]
                    rho2 = make_density(rho2_ket)
                    pre1 = pre_vals[best]
            if trials > max_trials:
                break
            p = 1 - pre1 / hs_distance(rho1, rho2)
            dist1 = hs_distance(rho0, p * rho1 + (1 - p) * rho2)
            if 0 <= p <= 1 and dist1 < dist0:
                itr += 1
                rho1 = p * rho1 + (1 - p) * rho2
                dist0 = dist1
                rho1_list.append(rho1)
                dist_list.append(dist0)
                if progress_cb:
                    progress_cb(itr, max_iter, trials, max_trials, dist0)
            rho2_ket = random_pure_dl(dim_list)
            rho2 = make_density(rho2_ket)
            pre1 = pre_sel(rho0, rho1, rho2)
            trials += 1
    return rho1, dist0, trials, dist_list

def gilbert_only_dist(rho_in: np.array, dim_list: np.array, max_iter: int, max_trials: int, opt_state="on", rng_seed=666, rho1_in=None):
    """
    Approximate the Closest Separable State (CSS) to the given state rho_in using Gilbert's algorithm
    :param rho_in: matrix
    :param dim_list: list of subsystem dimensions (int)
    :param max_iter: max iterations/corrections
    :param max_trials: maximum trials
    :param rng_seed: seed for RNG
    :param opt_state: Optimization On/Off, default "on"
    :param rho1_in: Optional start state
    # :param file_out: output file for the list of corrections
    :return: CSS, min HS-distance, number of trials
    """

    np.random.seed(rng_seed)
    rho0 = rho_in
    #print(rho0)
    if rho1_in is None:
        rho1 = np.diag(np.diag(rho0))
    else:
        rho1 = rho1_in
    # ndim = np.multiply.reduce(dim_list)
    print(rho1)
    rho2_ket = random_pure_dl(dim_list)
    rho2 = make_density(rho2_ket)
    dist0 = hs_distance(rho0, rho1)
    trials = 1
    decrement = 0.
    basis_unitary = [gell_mann_basis(x) for x in dim_list]
    pre1 = pre_sel(rho0, rho1, rho2)
    pre2 = 0.
    itr = 1
    rho1_list = [rho1]
    dist_list = [dist0]
    rho3 = rho0 - rho1
    herm = [np.eye(d, dtype=complex) for d in dim_list]
    if opt_state.lower() == "on":
        while itr <= max_iter and trials <= max_trials:
            # if itr % 5 == 0:
            #       print(itr, dist0)
            print(itr, dist0)

            while pre1 < 0 and trials <= max_trials:
                rho2_ket = random_pure_dl(dim_list)
                rho2 = make_density(rho2_ket)
                pre1 = pre_sel(rho0, rho1, rho2)
                trials += 1
            if trials > max_trials:
                break

            pre1, rho2, rho2_ket = optimize_rho2(rho0, rho1, rho2_ket, rho2, rho3, pre1, dim_list, basis_unitary, herm)
            p = 1 - pre1 / hs_distance(rho1, rho2)
            dist1 = hs_distance(rho0, p * rho1 + (1 - p) * rho2)
            decrement = dist0 - dist1
            if 0 <= p <= 1 and dist1 < dist0:
                itr += 1
                rho1 = p * rho1 + (1 - p) * rho2
                rho3 = rho0 - rho1
                decrement = dist0 - dist1
                dist0 = dist1
                rho1_list.append(rho1)
                dist_list.append(dist0)
            if decrement < 0.0000001:
                rho2_ket = random_pure_dl(dim_list)
                rho2 = make_density(rho2_ket)
            pre1 = pre_sel(rho0, rho1, rho2)
            trials += 1
    else:
        while itr < max_iter and trials <= max_trials:
            print(itr, dist0)

            while pre1 < 0 and trials <= max_trials:
                rho2_ket = random_pure_dl(dim_list)
                rho2 = make_density(rho2_ket)
                pre1 = pre_sel(rho0, rho1, rho2)
                trials += 1
            if trials > max_trials:
                break
            p = 1 - pre1 / hs_distance(rho1, rho2)
            dist1 = hs_distance(rho0, p * rho1 + (1 - p) * rho2)
            if 0 <= p <= 1 and dist1 < dist0:
                itr += 1
                rho1 = p * rho1 + (1 - p) * rho2
                dist0 = dist1
                rho1_list.append(rho1)
                dist_list.append(dist0)
            rho2_ket = random_pure_dl(dim_list)
            rho2 = make_density(rho2_ket)
            pre1 = pre_sel(rho0, rho1, rho2)
            trials += 1
    return dist0

def make_density(ket):
    return ket @ np.transpose(np.conjugate(ket))


def get_diagonal(rho):
    return np.diag(np.diag(rho))

def generate_report(dist):

    red_dist = dist[int(len(dist)/3):]

    plt.plot(red_dist)
    plt.title('H-S distance corrections')
    plt.show()
    plt.savefig("dist-series.pdf")

 