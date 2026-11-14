"""Reproduce all supplementary figures for Power System Analysis, Lectures 9-12.

Run: python generate_figures.py
Dependencies: numpy, matplotlib. Figures are written to ../图片/.
All examples are educational models, with assumptions stated in the notes.
Numerical checks below verify the defining equations, not rounded slide values.
"""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '图片'
OUT.mkdir(exist_ok=True)
available = {f.name for f in font_manager.fontManager.ttflist}
font = next((f for f in ['Microsoft YaHei', 'Noto Sans CJK SC', 'SimHei'] if f in available), 'DejaVu Sans')
plt.rcParams.update({'font.family': font, 'font.size': 11, 'axes.unicode_minus': False,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.alpha': .18, 'figure.facecolor': 'white',
                     'savefig.facecolor': 'white', 'axes.titlepad': 12})
BLUE, TEAL, ORANGE, RED = '#2563eb', '#0d9488', '#ea8b20', '#dc4654'
RESULTS = {}


def save(fig, name, subtitle):
    fig.text(.5, .012, subtitle, ha='center', fontsize=9, color='#526075')
    fig.tight_layout(rect=(0, .055, 1, 1))
    fig.savefig(OUT / name, dpi=170)
    plt.close(fig)


def mismatch(x):
    a, v = x
    return np.array([-4 - 10*v*np.sin(a), -9.9*v*v + 10*v*np.cos(a)])


def solve_two_bus(method):
    x, hist = np.array([0., 1.]), []
    for _ in range(100):
        mis = mismatch(x)
        hist.append(float(max(abs(mis))))
        if hist[-1] < 1e-11:
            break
        a, v = x
        if method == 'NR':
            jac = np.array([[10*v*np.cos(a), 10*np.sin(a)],
                            [10*v*np.sin(a), 19.8*v - 10*np.cos(a)]])
            x += np.linalg.solve(jac, mis)
        else:
            # B' = B'' = -9.9. Re-evaluate Q after the angle update.
            x[0] += mis[0] / (9.9*v)
            x[1] += mismatch(x)[1] / (9.9*v)
    assert max(abs(mismatch(x))) < 1e-10
    return x, hist


def lecture9():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, rx in zip(axes, [.05, 1.]):
        r, reactance, v, a = .2*rx, .2, .98, -.08
        y = 1 / complex(r, reactance)
        g, b = (-y).real, (-y).imag
        # Off-diagonal Y21 = g+jb, diagonal Y22 = y.
        gii, bii = y.real, y.imag
        p = v*v*gii + v*(g*np.cos(a)+b*np.sin(a))
        q = -v*v*bii + v*(g*np.sin(a)-b*np.cos(a))
        jac = np.array([[-q-v*v*bii, p+v*v*gii],
                        [p-v*v*gii, q-v*v*bii]])
        vals = abs(jac) / np.max(abs(jac))
        ax.imshow(vals, vmin=0, vmax=1, cmap='Blues')
        ax.grid(False)
        ax.set_xticks([0, 1], [r'$\delta$', r'$\ln U$'])
        ax.set_yticks([0, 1], [r'$P$', r'$Q$'])
        ax.set_title(f'R/X = {rx:g}：归一化灵敏度 / sensitivity')
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f'{vals[i,j]:.2f}', ha='center', va='center',
                        color='white' if vals[i,j]>.55 else '#183153', fontsize=19)
    save(fig, '自绘-09-jacobian-coupling.png',
         '自绘 / Model: U1=1, U2=0.98, δ2=-0.08 rad, X=0.2 pu；每幅以本幅最大绝对值归一化')

    fig, ax = plt.subplots(figsize=(9, 4.8))
    for method, color, label in [('NR', BLUE, '完整 Newton-Raphson'), ('FD', ORANGE, '常数 B 的 PQ 分解')]:
        x, hist = solve_two_bus(method)
        ax.semilogy(range(len(hist)), hist, 'o-', color=color, ms=4, label=label)
        RESULTS[method] = {'voltage': float(x[1]), 'angle_deg': float(np.degrees(x[0])),
                           'residual': hist[-1], 'iterations': len(hist)-1}
    ax.axhline(1e-4, color=TEAL, ls='--', label=r'示例容差 $10^{-4}$')
    ax.set(xlabel='完整迭代次数 / complete iterations', ylabel=r'$\max(|\Delta P|,|\Delta Q|)$ / pu',
           title='近似修正矩阵仍可收敛到相同潮流解 / Same root, different convergence')
    ax.legend()
    save(fig, '自绘-09-convergence.png', '自绘 / 课件 P19-P22 两节点数据；同一平启动；PQ 法每步仍重算完整非线性功率残差')


def lecture10():
    fig, ax = plt.subplots(figsize=(9, 5))
    u = np.linspace(0, 1.16, 600)
    for e, color in [(1., BLUE), (1.1, TEAL)]:
        ax.plot(u, u*(e-u)/.3, color=color, label=f'电源曲线 E={e:.1f}')
    for q, color in [(.3, ORANGE), (.5, RED)]:
        ax.axhline(q, color=color, ls='--', label=f'恒无功负荷 Q={q:.1f}')
        roots = np.roots([1, -1, .3*q])
        ax.scatter(roots, [q,q], color=color, zorder=4)
    ax.annotate('同一 E：负荷无功增加\n高电压交点向左移动', xy=(.816, .5), xytext=(.11, .84),
                arrowprops={'arrowstyle':'->', 'color':RED}, color=RED)
    ax.set(xlabel='负荷电压 U / pu', ylabel='无功 Q / pu', ylim=(-.05, 1.1),
           title=r'无功平衡是曲线交点：$Q=U(E-U)/X$')
    ax.legend(loc='upper right', fontsize=10)
    save(fig, '自绘-10-qu-intersection.png', '自绘 / 简化模型 X=0.3 pu、δ≈0、恒 Q 负荷；仅解释静态交点，不据此判定动态稳定性')

    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    u = np.linspace(.4, 1.1, 250)
    ax.plot(u, u*u, color=BLUE, lw=2.4, label=r'电容器 / SVC 容性极限：$Q/Q_N=U^2$')
    ax.plot(u, u, color=TEAL, lw=2.4, label=r'理想限流无功装置：$Q/Q_N=U$')
    ax.scatter([.7,.7], [.49,.7], color=[BLUE,TEAL], zorder=5)
    ax.annotate('U=0.7：仅余 49%', (.7,.49), xytext=(.75,.25), arrowprops={'arrowstyle':'->'}, fontsize=10)
    ax.set(xlabel=r'$U/U_N$', ylabel=r'$Q_{max}/Q_N$', title='低电压时的无功支撑能力 / Voltage-dependent reactive support')
    ax.legend(loc='upper left', fontsize=10)
    save(fig, '自绘-10-reactive-support.png', '自绘 / 归一化比较；限流曲线是假定纯无功电流、固定电流上限的补充模型，不代表所有装置的完整能力曲线')

    t = np.linspace(0, 1, 100)
    drop = .01 + .04*t
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for title, pilot, color in [('逆调压 / inverse',1+.05*t,BLUE),
                                 ('恒调压 / constant',np.full_like(t,1.035),TEAL),
                                 ('顺调压 / forward',1.065-.025*t,ORANGE)]:
        axes[0].plot(t,pilot,color=color,label=title)
        axes[1].plot(t,pilot-drop,color=color,label=title)
    for ax, title in zip(axes,['中枢点电压 / pilot voltage','负荷点电压 / receiving voltage']):
        ax.set(xlabel='轻载 → 重载 / normalized load',ylabel='电压 / pu',title=title)
        ax.legend(fontsize=9)
    save(fig, '自绘-10-voltage-strategies.png', '自绘 / 示例压降 ΔU=0.01+0.04t pu；三组给定值仅解释趋势，不是电压标准或实际调度数据')


def simulate_frequency(h, secondary):
    dt = .02
    t = np.arange(0,180+dt/2,dt)
    states = np.zeros((len(t),3))
    # x = Δf/fN; all powers use 1000 MW base. D=1, Kg=20, Tg=0.5s.
    def fun(time,s):
        x, pm, ps = s
        disturbance = .1 if time >= 5 else 0.
        return np.array([(pm-disturbance-x)/(2*h),
                         (-pm-20*x+ps)/.5,
                         -2*x if secondary and time >= 40 else 0.])
    for k in range(len(t)-1):
        a = fun(t[k],states[k]); b = fun(t[k]+dt/2,states[k]+dt*a/2)
        c = fun(t[k]+dt/2,states[k]+dt*b/2); d = fun(t[k]+dt,states[k]+dt*c)
        states[k+1] = states[k]+dt*(a+2*b+2*c+d)/6
    return t,states


def lecture11():
    fig, axes = plt.subplots(1,2,figsize=(11,4.8))
    f = np.linspace(49.65,50.1,100)
    base, kg, kd, step = 1000.,400.,20.,100.
    gen = base-kg*(f-50)
    load0 = base+kd*(f-50); load1 = load0+step
    primary = 50-step/(kg+kd)
    for ax in axes:
        ax.plot(gen,f,color=BLUE,label='原发电特性')
        ax.plot(load0,f,color='#94a3b8',ls=':',label='原负荷')
        ax.plot(load1,f,color=ORANGE,label='增加 100 MW 后负荷')
        ax.axhline(50,color='#94a3b8',lw=.8)
        ax.scatter([base],[50],color='#64748b',zorder=5)
        ax.set(xlabel='有功功率 P / MW',ylabel='频率 f / Hz')
    axes[0].scatter([base-kg*(primary-50)],[primary],color=RED,zorder=5)
    axes[0].set_title(f'一次调频：f={primary:.3f} Hz')
    axes[1].plot(gen+step,f,color=TEAL,label='二次调频后发电特性')
    axes[1].scatter([1100],[50],color=TEAL,zorder=5)
    axes[1].set_title('二次调频：平移特性，恢复 50 Hz')
    axes[0].legend(fontsize=9);axes[1].legend(fontsize=8)
    save(fig, '自绘-11-frequency-static.png', '自绘 / KG=400 MW/Hz，KD=20 MW/Hz；无饱和、忽略网损变化；二次调频增量 100 MW')

    fig, axes = plt.subplots(1,2,figsize=(11,4.8))
    for h,color in [(5.,BLUE),(2.5,ORANGE)]:
        t,s = simulate_frequency(h,False)
        axes[0].plot(t,50*(1+s[:,0]),color=color,label=f'H={h:g} s')
    axes[0].set(xlim=(4,18),xlabel='时间 / s',ylabel='频率 / Hz',title='惯量影响初始下降速度')
    for sec,color,label in [(False,ORANGE,'仅一次调频'),(True,TEAL,'一次 + 二次调频')]:
        t,s = simulate_frequency(5.,sec)
        axes[1].plot(t,50*(1+s[:,0]),color=color,label=label)
        if sec:
            RESULTS['frequency_final_hz'] = float(50*(1+s[-1,0]))
    axes[1].axvline(40,color='#94a3b8',ls=':',label='40 s 启用积分调节')
    axes[1].set(xlabel='时间 / s',ylabel='频率 / Hz',title='一次调频留有静差，二次调频恢复频率')
    for ax in axes: ax.legend(fontsize=9)
    save(fig, '自绘-11-frequency-dynamics.png', '自绘 / 聚合小信号模型：1000 MW 基准，5 s 增载 0.1 pu，D=1，KG*=20，Tg=0.5 s，Ki=2；非实际系统录波')
    assert abs(RESULTS['frequency_final_hz']-50)<1e-5


def dispatch(pd):
    b,c,lower,upper = np.array([450.,430.]),np.array([.1,.03]),np.array([150.,100.]),np.array([300.,900.])
    assert sum(lower)-1e-10 <= pd <= sum(upper)+1e-10
    lo,hi=400.,600.
    for _ in range(90):
        lam=(lo+hi)/2; p=np.clip((lam-b)/(2*c),lower,upper)
        if sum(p)<pd: lo=lam
        else: hi=lam
    return np.clip(((lo+hi)/2-b)/(2*c),lower,upper),(lo+hi)/2


def loss_ed():
    lo,hi=50.,300.
    for _ in range(100):
        p2=(lo+hi)/2; p1=350+.001*(p2-50)**2-p2
        diff=(.07*p2+41)/(1.1-.002*p2)-(.07*p1+41)
        if diff>0: hi=p2
        else: lo=p2
    p2=(lo+hi)/2; pl=.001*(p2-50)**2; p1=350+pl-p2
    assert abs(p1+p2-pl-350)<1e-10
    assert abs((.07*p2+41)/(1.1-.002*p2)-(.07*p1+41))<1e-9
    return p1,p2,pl,.07*p1+41


def lecture12():
    pstar=22/.26
    total=lambda p: 9000+450*p+.1*p*p+25000+430*(700-p)+.03*(700-p)**2
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    p=np.linspace(0,700,500)
    axes[0].plot(p,total(p)/1e4,color=BLUE)
    axes[0].scatter([pstar,150],[total(pstar)/1e4,total(150)/1e4],color=[TEAL,RED],zorder=5)
    axes[0].axvspan(150,300,color=TEAL,alpha=.12,label='补充约束下可行区')
    axes[0].set(xlabel='P1 / MW（P2=700−P1）',ylabel='总成本 / 万元每小时',title='等微增率对应总成本极小点')
    axes[0].legend(fontsize=9)
    axes[1].plot(p,450+.2*p,color=BLUE,label=r'$IC_1(P_1)$')
    axes[1].plot(p,430+.06*(700-p),color=ORANGE,label=r'$IC_2(700-P_1)$')
    axes[1].axvline(pstar,color=TEAL,ls='--',label=f'无约束 P1={pstar:.2f}')
    axes[1].axvline(150,color=RED,ls=':',label='补充下限 P1=150')
    axes[1].set(xlabel='P1 / MW',ylabel='微增率 / 元每 MWh',title='边界最优点允许微增率不相等')
    axes[1].legend(fontsize=9)
    save(fig, '自绘-12-economic-dispatch.png', '自绘 / 课件 P21 成本；补充边界 150≤P1≤300、100≤P2≤900 MW；总负荷 700 MW')
    RESULTS['ed_unbounded']={'p1':pstar,'p2':700-pstar,'lambda':450+.2*pstar,'cost':total(pstar)}
    RESULTS['ed_bounded']={'p1':150.,'p2':550.,'cost':total(150)}

    # Use interior demand values to show the one-sided marginal cost at endpoints.
    demands=np.linspace(250.001,1199.999,500)
    res=[dispatch(x) for x in demands]
    powers=np.array([x[0] for x in res]); lam=np.array([x[1] for x in res])
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    axes[0].plot(demands,powers[:,0],color=BLUE,label='机组 1')
    axes[0].plot(demands,powers[:,1],color=ORANGE,label='机组 2')
    axes[1].plot(demands,lam,color=TEAL)
    for ax in axes:
        for limit in [150+(480-430)/.06,1070]: ax.axvline(limit,color='#94a3b8',ls=':')
        ax.set_xlabel('系统负荷 / MW')
    axes[0].set(ylabel='最优出力 / MW',title='机组到达边界后，其余机组接力')
    axes[0].legend();axes[1].set(ylabel='λ / 元每 MWh',title='系统边际成本随活跃约束改变斜率')
    save(fig, '自绘-12-dispatch-bounds.png', '自绘 / 同一补充边界与成本；PD≈983.33 MW 时机组1离开下限，PD=1070 MW 时机组2达到上限')
    for pd in [250,700,150+(480-430)/.06,1070,1200]:
        p,_=dispatch(pd);assert abs(sum(p)-pd)<1e-8

    p1,p2,pl,lam=loss_ed()
    RESULTS['loss_ed']={'p1':p1,'p2':p2,'loss':pl,'lambda':lam}
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    p=np.linspace(50,220,400); pother=350+.001*(p-50)**2-p
    cost=lambda z:41*z+.035*z*z
    axes[0].plot(p,(cost(pother)+cost(p))/1e4,color=BLUE)
    axes[0].scatter([p2],[(cost(p1)+cost(p2))/1e4],color=TEAL,zorder=5)
    axes[0].axvline(p2,color=TEAL,ls='--',label=f'最优 P2={p2:.3f} MW')
    axes[0].set(xlabel='远端机组 P2 / MW',ylabel='变动成本之和 / 万元每小时',title='相同机组，含网损时出力不相等')
    axes[0].legend(fontsize=9)
    axes[1].plot(p,41+.07*pother,color=BLUE,label=r'$IC_1$（负荷侧）')
    axes[1].plot(p,(41+.07*p)/(1.1-.002*p),color=ORANGE,label=r'$\alpha_2 IC_2$（远端）')
    axes[1].axhline(lam,color=TEAL,ls=':',label=f'λ={lam:.3f}')
    axes[1].set(xlabel='远端机组 P2 / MW',ylabel='修正微增率 / 元每 MWh',title='负荷侧每多收到 1 MW 的成本相等')
    axes[1].legend(fontsize=9)
    save(fig, '自绘-12-loss-penalty.png', '自绘 / 课件 P28 模型：PD=350 MW，PL=0.001(P2−50)²；每个扫描点均严格满足 P1+P2−PL=350')


if __name__ == '__main__':
    lecture9(); lecture10(); lecture11(); lecture12()
    (Path(__file__).parent/'calculated_results.json').write_text(
        json.dumps(RESULTS,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(RESULTS,ensure_ascii=False,indent=2))
