# jqtrade

jqtrade是一个用户本地运行实盘任务的框架, 它提供以下功能：
1. 策略代码框架. 用户可以在策略代码中使用run_daily设置定时任务, 定时运行自己定义的函数. 
2. 交易和账户管理相关API. 用户可以通过这些API实现实盘下单、撤单、查询资金、持仓功能. 
3. 为用户提供默认的实盘交易接口. 在jqtrade内部, 已经默认实现了对接安信证券one quant DMA交易的接口, 可以直接通过上述API与你的资金账户进行交互. 只需在策略中设置好资金账户和交易接口配置即可.  



# 快速上手
## 安装
1. 安装python. 需要安装>=3.6.13的python版本, 可以参考python官网的安装介绍. 
2. 安装jqtrade. 
```bash
pip install jqtrade
```
3. 申请并安装安信one quant DMA算法使用权限. 申请步骤：【待补充】. 如果你对 python熟悉, 且有自己的实盘接口渠道, 可以自己实现一个jqtrade.account.AbsTradeGate的子类来替换jqtrade中默认的trade gate

## 策略代码
完成上述安装步骤之后, 就可以开始实现策略代码了, 下面是一个策略代码的示例：
```python
# -*- coding: utf-8 -*-

def process_initialize(context):
    log.info("process_initialize run.")

    set_options(
        account_no="1234567",           # 资金账号
    )
    
    run_daily(before_market_open, "open-30m")
    run_daily(market_open, "open")
    run_daily(market_close, "close")
    run_daily(after_market_close, "close+30m")
    run_daily(do_order, "every_minute")


# 自定义的全局变量, 策略进程退出时会释放, 若需持久化, 请直接在策略代码中写到文件中
g = {}


def before_market_open(context):
    log.info("before_market_open run")

    log.info(f"当前总资产： {context.portfolio.total_assert}")
    log.info(f"当前锁定金额：{context.portfolio.locked_cash}")
    log.info(f"当前可用资金：{context.portfolio.available_cash}")
    log.info(f"当前多头持仓：{context.portfolio.long_positions}")
    log.info(f"当前空头持仓：{context.portfolio.short_positions}")

    
def market_open(context):
    log.info("market_open run")
    
    
def do_order(context):
    log.info("do_order run")

    pos = context.portfolio.long_positions["000001.XSHE"]
    if pos.available_amount > 0:
        g["order_id_000001"] = order("000001.XSHE", -pos.available_amount, LimitOrderStyle(10))
    
    if "000002.XSHE" not in context.portfolio.long_positions:
        g["order_id_000002"] = order("000002.XSHE", 100, MarketOrderStyle())
    
    orders = get_orders()
    for _order in orders:
        if _order.status in ("new", "open"):
            log.info(f"查询到未完成订单：{_order}")
            cancel_order(_order.order_id)

    
def market_close(context):
    log.info("market_close run")

    
def after_market_close(context):
    log.info("after_market_close run")
```

策略代码中提供了基本下单、撤单、查询资金、持仓、订单的API接口, 关于这些API的详细使用, 见下面：【】

## 启动策略
jqtrade提供了start_task命令可以很方便的快速启动实盘策略. 

示例：
```bash
# 启动一个策略名称为'demo'的实盘策略, 策略代码路径是'strategies/demo_strategy.py'
python -m jqtrade start_task -c strategies/demo_strategy.py -n
```
或
```bash
jqtrade start_task -c strategies/demo_strategy.py -n demo
```

*注意*:
* 实盘策略的名称需要唯一, 不能在同一台机器上启动多个相同名称的实盘任务
* 策略代码所在目录会自动添加到sys.path, 因此你可以在策略代码中导入你自定义的模块（支持.py和.so模块, 导入.so模块时, 请注意是否与当前python版本匹配）



## 查看当前运行的策略
如果你想查看当前机器上运行了哪些实盘任务, 可以使用get_tasks命令. 

示例：
```bash
# 启动一个策略名称为'demo'的实盘策略, 策略代码路径是'strategies/demo_strategy.py'
python -m jqtrade get_tasks
```
或
```bash
jqtrade get_tasks
```

## 停止运行中的策略
如果你想停止当前机器上运行的某个实盘任务, 可以使用stop_task命令. 

```bash
python -m jqtrade stop_task -n demo
```
或
```bash
jqtrade stop_task -n demo
```

start_task、stop_task除了上述示例中的常用参数之外, 还有其他更详细的命令介绍, 见：【】

## 命令参考
在安装完jqtrade之后, 就可以使用`python -m jqtrade`或直接使用`jqtrade`来执行相关命令了. 

jqtrade目前提供了三个子命令, 分别是：
* start_task: 启动策略进程
* stop_task: 停止策略进程
* get_tasks: 查询策略进程

jqtrade本身以及其每一个子命令都可以使用 `-h` 选项查看子命令的详细参数和介绍.

获取子命令介绍：
```bash
# jqtrade --help
usage: __main__.py [-h] {start_task,get_tasks,stop_task} ...

positional arguments:
  {start_task,get_tasks,stop_task}
    start_task          创建新的实盘任务
    get_tasks           查询当前运行中的实盘任务
    stop_task           停止运行中的实盘任务

optional arguments:
  -h, --help            show this help message and exit
```

获取start_task介绍：
```bash
# jqtrade start_task --help 
usage: __main__.py start_task [-h] -n NAME -c CODE [-o OUT] [-e ENV] [--config CONFIG] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  实盘任务名称, 唯一标识该实盘任务, 不能重复
  -c CODE, --code CODE  策略代码路径
  -o OUT, --out OUT     日志路径, 不指定时打印到标准输出/错误
  -e ENV, --env ENV     指定实盘策略进程运行环境变量, 多个环境变量使用分号分隔, 示例: -e PYTHONPATH=./package;USER=test
  --config CONFIG       指定自定义配置文件路径
  --debug               是否开启debug模式, debug模式日志更丰富些
```

### start_task
```bash
start_task [-h] -n NAME -c CODE [-o OUT] [-e ENV] [--config CONFIG] [--debug]
```
start_task用于启动策略进程, 该子命令选项如下：
* 必须提供:
    * -n NAME, --name NAME: 实盘任务名称, 唯一标识该实盘任务, 同一台机器不能重复
    * -c CODE, --code CODE: 策略代码路径
* 可选项:
    * -o OUT, --out OUT: 日志路径, 不指定时打印到控制台标准输出/错误
    * -e ENV, --env ENV: 指定实盘策略进程运行环境变量, 多个环境变量使用分号分隔. 示例: -e PYTHONPATH=./package;USER=test
    * --debug: 是否开启debug模式, debug模式日志更丰富些，会包含更多的jqtrade系统日志.
    * --config CONFIG: 指定自定义配置文件路径, 除非你对jqtrade的配置管理很熟悉, 否则不建议使用.

示例:
```bash
jqtrade start_task -c strategies/demo.py -n demo -o demo.log -e 'PYTHONPATH=/home/server/strategy_utils'
```

*注意：`-e` 指定的环境变量，对于PYTHONPATH，jqtrade会将指定的路径信息insert到sys.path中*

### stop_task
```bash
stop_task [-h] [-n NAME] [-p PID] [--all] [-s {SIGTERM,SIGKILL}]
```
stop_task用于停止运行中的策略进程，该子命令选项如下：
* 以下三个选项至少提供一个:
    * -n NAME, --name NAME: 通过指定实盘名称来停止实盘
    * -p PID, --pid PID: 通过指定实盘进程pid来停止实盘, 策略进程的pid可以通过 `get_tasks` 命令查询到，或直接通过系统查询
    * --all: 停止所有运行中的实盘任务, 当指定此选项的时候，会忽略`-n`和`-p`选项
* 可选项:
    * -s {SIGTERM,SIGKILL}, --signal {SIGTERM,SIGKILL}: 停止策略进程时使用的信号，默认SIGTERM，希望强制退出时请使用SIGKILL。

*注意*:
* 如果你的策略进程没有后台运行，而是在当前终端对话框中正在运行的，可以直接使用`ctrl + c` 来快速停止策略。jqtrade内部会监听`ctrl + c`发送的信号，然后安全的停止当前策略进程
* 关于停止策略进程的时间:
    * 使用stop_task默认`SIGTERM`选项或`ctrl + c`来停止策略进程时，策略进程会在处理完当前的事务之后，再执行信号处理。
    * 使用`stop_task -s SIGKILL`时，策略进程会被系统直接杀掉，不管当前是否正在处理事务

## 策略框架
策略框架指jqtrade给用户提供了用来实现策略代码，将策略代码调度起来，执行用户自定义函数的框架.
jqtrade目前通过定时任务的机制来驱动策略执行, 用户只需要实现`process_initialize`函数，在该函数中调用jqtrade提供的`run_daily`函数，设置自己的定时任务即可。
当然，如果你要进行实盘交易，那么在策略运行时就需要在`process_initialize`中调用set_options选项来给交易接口传递一些必要初始化参数，比如资金账号、柜台类型等等

### process_initialize介绍
`process_initialize(context)`函数是用户需要在策略代码中自己定义并实现的一个函数，并且该函数要有一个参数`context`，在该函数中，用户需要设置交易接口所需的必要参数、定时任务。
`context`参数是jqtrade提供给用户的一个API对象，它具有一些属性方便用户来查询数据，详情见下面的介绍：【】

示例:
```python
# -*- coding: utf-8 -*-

def process_initialize(context):
    # 设置交易接口所需的账户信息
    set_options(account_no="1234567")
    
    # 设置定时任务
    run_daily(func, "09:30:00")


def func(context):
    pass
```

*注意*:
* process_initialize会在策略进程启动时先执行，因此，用户自己额外的一些初始化操作可以放到process_initialize中

### run_daily
`run_daily(func, time)`用于设置定时任务，参数介绍如下：
* func: 用户自己定义和实现的函数，该函数的位置参数为`context`
* time: 支持多种方式指定时间:
    * 格式为`HH:MM:SS`格式的时间字符串，比如`09:30:30`，支持精确到秒
    * open: 等价于`09:30:00`，jqtrade默认开盘时间是09:30:00
    * close: 等价于`15:00:00`, jqtrade默认收盘时间是15:00:00
    * every_minute: 等价于交易时间段每分钟执行(09:30:00~11:30:00, 13:00:00~15:00:00)

*注意*:
* `run_daily`只能在`process_initialize`中调用，在其他地方调用会报错。

### set_options
set_options


## 其他策略API
