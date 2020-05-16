import cupy as cp
import numpy as np
from solver.utils import inc_index
from solver.utils import dec_index


def gfo_cp_mark(x):
    v = x[0:(x.size-2)]
    value1 = x[x.size-2]
    value2 = x[x.size-1]
    #m,n=Sigma.shape
    first_block = Sigma@v -1/2*value1*mu -1/2*value2*unos
    second_block = -1/2*(v.dot(mu)-r)
    third_block = -1/2*(v.dot(unos)-1)
    first_block_np = cp.asnumpy(first_block)
    second_block_np = cp.asnumpy(second_block)
    third_block_np = cp.asnumpy(third_block)
    #es necesario pasar los bloques a numpy para poder hacerles concatenate 
    return cp.asarray(np.concatenate((first_block_np,np.array([second_block_np]),np.array([third_block_np]))))



def Hfo_cp_mark(x):
    v = x[0:(x.size-2)]
    value1 = x[x.size-2]
    value2 = x[x.size-1]
    m,n=Sigma.shape
    first_block = Sigma 
    second_block = -1/2*mu
    third_block = -1/2*unos
    fs_block = cp.column_stack((first_block, second_block, third_block))
    fourth_block = -1/2*mu
    fifth_block = -1/2*unos
    sixth_block = cp.zeros((2,2))
    #es necesario pasar los bloques a numpy para poder hacerles concatenate y row_stack
    tf_block = np.column_stack(( np.row_stack((cp.asnumpy(fourth_block),cp.asnumpy(fifth_block))),cp.asnumpy(sixth_block)))
    return cp.asarray(np.row_stack((cp.asnumpy(fs_block), tf_block)))



def gradient_approximation(f,x,h=1e-8):
    '''
    Numerical approximation of gradient for function f using forward differences.
    Args:
        f (lambda expression): definition of function f.
        x (array): numpy array that holds values where gradient will be computed.
        h (float): step size for forward differences, tipically h=1e-8
    Returns:
        gf (array): numerical approximation to gradient of f.
    '''
    n = x.size
    gf = cp.zeros(n)
    f_x = f(x)
    for i in np.arange(n):
        inc_index(x,i,h)
        gf[i] = f(x) - f_x
        dec_index(x,i,h)
    return gf/h



def Hessian_approximation(f,x,h=1e-6):
    '''
    Numerical approximation of Hessian for function f using forward differences.
    Args:
        f (lambda expression): definition of function f.
        x (array): numpy array that holds values where Hessian will be computed.
        h (float): step size for forward differences, tipically h=1e-6
    Returns:
        Hf (array): numerical approximation to Hessian of f.
    '''
    n = x.size
    Hf = cp.zeros((n,n))
    f_x = f(x)
    for i in np.arange(n):
        inc_index(x,i,h)
        f_x_inc_in_i = f(x)
        for j in np.arange(i,n):
            inc_index(x,j,h)
            f_x_inc_in_i_j = f(x)
            dec_index(x,i,h)
            f_x_inc_in_j = f(x)
            dif = f_x_inc_in_i_j-f_x_inc_in_i-f_x_inc_in_j+f_x
            Hf[i,j] = dif
            if j != i:
                Hf[j,i] = dif
            dec_index(x,j,h)
            inc_index(x,i,h)
        dec_index(x,i,h)
    return Hf/h**2

import solver



def Newtons_method_feasible_init_point(f, A, x_0, tol, 
                                       tol_backtracking, x_ast=None, p_ast=None, maxiter=30,
                                       gf_symbolic = None,
                                       Hf_symbolic = None):
    '''
    Newton's method to numerically approximate solution of min f subject to Ax = b.
    IMPORTANT: this implementation requires that initial point x_0, satisfies: Ax_0 = b
    Args:
        f (fun): definition of function f as lambda expression or function definition.
        A (numpy ndarray): 2d numpy array of shape (m,n) defines system of constraints Ax=b.
        x_0 (numpy ndarray): initial point for Newton's method. Must satisfy: Ax_0 = b
        tol (float): tolerance that will halt method. Controls stopping criteria.
        tol_backtracking (float): tolerance that will halt method. Controls value of line search by backtracking.
        x_ast (numpy ndarray): solution of min f, now it's required that user knows the solution...
        p_ast (float): value of f(x_ast), now it's required that user knows the solution...
        maxiter (int): maximum number of iterations
        gf_symbolic (fun): definition of gradient of f. If given, no approximation is
                                     performed via finite differences.
        Hf_symbolic (fun): definition of Hessian of f. If given, no approximation is
                                     performed via fi
                                     nite differences.
    Returns:
        x (numpy ndarray): numpy array, approximation of x_ast.
        iteration (int): number of iterations.
        Err_plot (numpy ndarray): numpy array of absolute error between p_ast and f(x) with x approximation
                          of x_ast. Useful for plotting.
        x_plot (numpy ndarray): numpy array that containts in columns vector of approximations. Last column
                        contains x, approximation of solution. Useful for plotting.
    '''
    iteration = 0
        
    x = x_0
    
    feval = f(x)
    
    if gf_symbolic:
        gfeval = gf_symbolic(x)
    else:
        gfeval = gradient_approximation(f,x)

    if Hf_symbolic:
        Hfeval = Hf_symbolic(x)
    else:
        Hfeval = Hessian_approximation(f,x)
    
    normgf = np.linalg.norm(gfeval)
    condHf= solver.utils.condicion_cupy(Hfeval)
    
    Err_plot_aux = np.zeros(maxiter)
    Err_plot_aux[iteration]= solver.utils.compute_error(p_ast,feval)
    
    Err = solver.utils.compute_error(x_ast,x)
    
        
    if(A.ndim == 1):
        p = 1
        n = x.size
        zero_matrix = cp.zeros(p)
        first_stack = cp.column_stack((Hfeval, A.T))
        second_stack = cp.row_stack((A.reshape(1,n).T,zero_matrix)).reshape(1,n+1)[0]
    else:
        p,n = A.shape
        zero_matrix = cp.zeros((p,p))
        first_stack = np.column_stack((Hfeval, A.T))
        second_stack = np.column_stack((A,zero_matrix))
        
    x_plot = cp.zeros((n,maxiter))
    x_plot[:,iteration] = x
    
    system_matrix = np.row_stack((first_stack,second_stack))
    zero_vector = cp.zeros(p)
    rhs = np.row_stack((gfeval.reshape(n,1), zero_vector.reshape(p,1))).T[0]

    #Newton's direction and Newton's decrement
    dir_desc = cp.linalg.solve(system_matrix, -rhs)
    dir_Newton = dir_desc[0:n]
    dec_Newton = -gfeval.dot(dir_Newton)
    w_dual_variable_estimation = dir_desc[n:(n+p)]


    print('I\tNormgf \tNewton Decrement\tError x_ast\tError p_ast\tline search\tCondHf')
    print('{}\t{}\t{}\t{}\t{}\t{}\t\t{}'.format(iteration,
                                                normgf,
                                                dec_Newton,
                                                Err,
                                                Err_plot_aux[iteration],"---",
                                                condHf))
    stopping_criteria = dec_Newton/2
    iteration+=1
    while(stopping_criteria>tol and iteration < maxiter):
        der_direct = -dec_Newton
        t = solver.line_search.line_search_by_backtracking(f,dir_Newton,x,der_direct)
        x = x + t*dir_Newton
        feval = f(x)
        
        
        if gf_symbolic:
            gfeval = gf_symbolic(x)
        else:
            gfeval = gradient_approximation(f,x)
        
        if Hf_symbolic: 
            Hfeval = Hf_symbolic(x)
        else:
            Hfeval = Hessian_approximation(f,x)
        if(A.ndim == 1):
            first_stack = cp.column_stack((Hfeval, A.T))
        else:
            first_stack = cp.column_stack((Hfeval, A.T))

        system_matrix = np.row_stack((first_stack,second_stack))
        rhs = np.row_stack((gfeval.reshape(n,1), zero_vector.reshape(p,1))).T[0]
        #Newton's direction and Newton's decrement
        dir_desc = cp.linalg.solve(system_matrix, -rhs)
        dir_Newton = dir_desc[0:n]
        dec_Newton = -gfeval.dot(dir_Newton)
        w_dual_variable_estimation = dir_desc[n:(n+p)]
        
        Err_plot_aux[iteration]= solver.utils.compute_error(p_ast,feval)
        x_plot[:,iteration] = x
        Err = solver.utils.compute_error(x_ast,x)
        print('{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(iteration,
                                                  normgf,
                                                  dec_Newton,Err,
                                                  Err_plot_aux[iteration],t,
                                                  cp.asarray(condHf)))
        stopping_criteria = dec_Newton/2
        if t<tol_backtracking: #if t is less than tol_backtracking then we need to check the reason
            iter_salida=iteration
            iteration = maxiter - 1
        iteration+=1
    print('{} {}'.format("Error of x with respect to x_ast:",Err))
    print('{} {}'.format("Approximate solution:", x))
    cond = Err_plot_aux > np.finfo(float).eps*10**(-2)
    Err_plot = Err_plot_aux[cond]
    
    if iteration == maxiter and t < tol_backtracking:
        print("Backtracking value less than tol_backtracking, check approximation")
        iteration=iter_salida
    else:
        if iteration == maxiter:
            print("Reached maximum of iterations, check approximation")
    x_plot = x_plot[:,:iteration]
    return [x,iteration,Err_plot,x_plot]
