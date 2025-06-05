from web3 import Web3
import web3 # 导入 web3 模块本身，用于检查版本号
from eth_account import Account
import os
import time # 导入 time 模块用于处理时间

# --- 配置 ---
# 替换为您的 RPC 节点 URL (例如 Infura, Alchemy, 或本地节点)
# 注意：请确保这是合约部署的网络 (主网, Goerli, Sepolia 等)
RPC_URL = "你的rpc"

# 合约地址
CONTRACT_ADDRESS = "0xF739D03e98e23A7B65940848aBA8921fF3bAc4b2"

# 交易的 data 字段 (MethodID + 编码后的参数)
TRANSACTION_DATA = "0xb1819c2b000000000000000000000000私钥对应的地址去除0x记得000000000000000000000000这个改为你地址上启动排序器后会有一笔Fulfill Basic Order_efficient_6GL6yc的交易获取把里面你创建的合约地址输入到这里删除0x"

# --- 固定的 Gas 设置 ---
FIXED_GAS_LIMIT = 300000
FIXED_GAS_PRICE_GWEI = 500 # 请根据网络情况调整此值，500 Gwei 在 Sepolia 通常非常高

# --- 私钥配置 (从文件读取) ---
# !!! 警告: 将私钥保存在文件中非常不安全 !!!
# 请将您的私钥放在这个文件中，确保文件中只有私钥字符串
PRIVATE_KEY_FILE_PATH = "private_key.txt" # 替换为您的私钥文件路径

# --- 定时发送配置 ---
# 目标开始发送的 Unix 时间戳
# 例如：获取当前时间戳 time.time()，或计算未来的时间戳 (例如使用 https://www.unixtimestamp.com/)
# !!! 您必须将这里替换为您希望开始发送交易的精确未来时间戳 !!!
TARGET_TIMESTAMP = 1746740920 # 替换为您实际的目标时间戳最好提前20秒

# 总共发送的交易次数
NUM_REPETITIONS = 20

# 每次发送之间等待的秒数
SEND_INTERVAL_SECONDS = 6

def get_private_key_from_file(file_path):
    """
    从指定文件中读取私钥。
    警告: 将私钥保存在普通文本文件中非常不安全。
    """
    try:
        with open(file_path, 'r') as f:
            private_key = f.readline().strip() # 读取第一行并去除首尾空白
            if not private_key:
                raise ValueError("文件为空或不包含私钥")
            # 可选：如果私钥没有 0x 前缀，可以加上
            if not private_key.startswith('0x'):
                 private_key = '0x' + private_key
            return private_key
    except FileNotFoundError:
        print(f"错误：私钥文件未找到：{file_path}")
        return None
    except Exception as e:
        print(f"读取私钥文件时发生错误：{e}")
        return None

def wait_until(timestamp):
    """
    等待直到达到指定的 Unix 时间戳。
    """
    while time.time() < timestamp:
        time_left = timestamp - time.time()
        if time_left > 0:
            print(f"等待 {time_left:.1f} 秒直到目标时间戳...")
            # 每隔一段时间更新或在剩余时间较少时频繁更新
            sleep_duration = min(5, max(1, time_left / 2)) # 动态调整睡眠时间
            time.sleep(sleep_duration)
        else:
            break # 理论上不会发生，但以防万一

def send_timed_repeated_contract_calls():
    """
    在指定时间戳开始，重复发送合约调用交易。
    """
    # 打印脚本实际使用的 web3 版本
    try:
        print(f"正在使用的 web3 版本: {web3.__version__}")
        if web3.__version__ < '7.0.0':
             print("警告：web3 版本可能过旧，建议升级到 7.0.0 或更高版本以获得最佳兼容性。")
    except Exception as e:
        print(f"警告：无法获取 web3 版本信息。错误：{e}")

    # 获取私钥
    private_key = get_private_key_from_file(PRIVATE_KEY_FILE_PATH)
    if not private_key:
        print("错误：无法获取私钥。请检查文件路径和内容。")
        return

    # 1. 连接到以太坊节点
    try:
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if not w3.is_connected():
            print(f"错误：无法连接到 RPC 节点 {RPC_URL}")
            return
        print(f"成功连接到节点：{RPC_URL}")
        chain_id = w3.eth.chain_id
        print(f"当前链 ID：{chain_id}")
    except Exception as e:
        print(f"连接节点时发生错误：{e}")
        return

    # 2. 准备发送账户
    try:
        account = Account.from_key(private_key) # 使用从文件中读取的私钥
        sender_address = account.address
        print(f"发送方地址：{sender_address}")
        # 检查账户余额 (可选但推荐)
        balance_wei = w3.eth.get_balance(sender_address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        print(f"发送方余额：{balance_eth:.4f} ETH")
        if balance_eth <= 0:
             print("警告：发送方余额为零，可能无法支付 gas 费用。")

    except Exception as e:
        print(f"处理私钥或获取账户信息时发生错误：{e}")
        return

    # 3. 获取起始 Nonce
    # 获取当前发送方地址的交易计数作为起始 Nonce
    try:
        start_nonce = w3.eth.get_transaction_count(sender_address)
        print(f"起始 Nonce：{start_nonce}")
    except Exception as e:
        print(f"错误：无法获取 Nonce。错误：{e}")
        return

    # --- 等待直到目标开始时间 ---
    print(f"目标开始发送时间戳：{TARGET_TIMESTAMP}")
    wait_until(TARGET_TIMESTAMP)
    print("达到目标时间，开始发送交易...")

    # --- 重复发送交易 ---
    sent_tx_hashes = [] # 用于存储发送成功的交易哈希

    for i in range(NUM_REPETITIONS):
        current_repetition = i + 1
        current_nonce = start_nonce + i # Nonce 每次加 1

        print(f"\n--- 正在发送第 {current_repetition}/{NUM_REPETITIONS} 笔交易 (Nonce: {current_nonce}) ---")

        # 4. 构建交易字典 (使用固定的 Gas 设置和递增的 Nonce)
        transaction = {
            'from': sender_address,
            'to': CONTRACT_ADDRESS,
            'value': 0, # 通常合约写操作不发送 ETH
            'data': TRANSACTION_DATA,
            'nonce': current_nonce, # <-- 使用当前 Nonce
            'chainId': chain_id,
            'gas': FIXED_GAS_LIMIT, # <-- 使用固定的 Gas Limit
        }

        # 使用 Legacy Gas Price
        fixed_gas_price_wei = w3.to_wei(FIXED_GAS_PRICE_GWEI, 'gwei')
        transaction['gasPrice'] = fixed_gas_price_wei
        print(f"使用固定的 Gas Price: {FIXED_GAS_PRICE_GWEI} Gwei")

        try:
            # 5. 签名交易
            # 直接使用 account 对象签名交易字典
            signed_transaction = account.sign_transaction(transaction)
            print("交易签名成功。")

            # 获取原始交易数据
            raw_tx = None
            if hasattr(signed_transaction, 'raw_transaction'):
                raw_tx = signed_transaction.raw_transaction
                # print("使用属性: raw_transaction")
            elif hasattr(signed_transaction, 'rawTransaction'):
                raw_tx = signed_transaction.rawTransaction
                # print("使用属性: rawTransaction")
            elif hasattr(signed_transaction, 'raw'):
                raw_tx = signed_transaction.raw
                # print("使用属性: raw")
            else:
                raise AttributeError("无法找到原始交易数据属性 (raw, rawTransaction, raw_transaction)")

            if raw_tx is None:
                 raise ValueError("未能获取到原始交易数据")

            # 6. 发送交易
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            print(f"交易已发送，哈希：{tx_hash.hex()}")
            sent_tx_hashes.append(tx_hash) # 记录发送成功的哈希

        except Exception as e:
            print(f"发送第 {current_repetition} 笔交易时发生错误：{e}")
            # 如果发送失败，根据需要决定是否中止或继续 (这里选择继续)

        # 7. 间隔发送 (除了最后一次)
        if current_repetition < NUM_REPETITIONS:
            print(f"等待 {SEND_INTERVAL_SECONDS} 秒发送下一笔...")
            time.sleep(SEND_INTERVAL_SECONDS)

    print("\n--- 所有交易发送尝试完成 ---")
    print(f"共发送成功 {len(sent_tx_hashes)} 笔交易的哈希。")

    # --- 等待所有交易确认 (可选，可能需要很长时间) ---
    if sent_tx_hashes:
        print("\n--- 正在等待所有已发送交易的确认 ---")
        for i, tx_hash in enumerate(sent_tx_hashes):
            try:
                print(f"等待第 {i+1}/{len(sent_tx_hashes)} 笔交易确认 (哈希: {tx_hash.hex()})...")
                tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=900) # 增加超时时间
                print(f"交易 {tx_hash.hex()} 确认成功！")
                if tx_receipt.status == 1:
                    print("交易状态：成功")
                else:
                    print("交易状态：失败 (请在浏览器查看)")
                # print(f"交易收据：{tx_receipt}\n") # 打印详细收据
            except Exception as e:
                print(f"等待交易 {tx_hash.hex()} 确认时发生错误或超时：{e}")
                print("请稍后在区块链浏览器上查询该交易哈希确认最终状态。")
        print("--- 所有交易确认等待完成 ---")
    else:
        print("没有交易成功发送，无需等待确认。")


# --- 运行脚本 ---
if __name__ == "__main__":
    # 在运行脚本前，请创建 PRIVATE_KEY_FILE_PATH 指定的文件，
    # 并将私钥（包含或不包含 0x 前缀）写入文件中。
    # 替换 RPC_URL 如果需要。
    # 根据需要调整 FIXED_GAS_LIMIT 和 FIXED_GAS_PRICE_GWEI。
    # !!! 必须将 TARGET_TIMESTAMP 替换为您希望开始发送交易的精确未来时间戳 !!!
    # !!! 必须将 NUM_REPETITIONS 替换为总共发送的次数 !!!

    print("--- 开始执行脚本 ---")
    # 调用新的主函数
    send_timed_repeated_contract_calls()
    print("--- 脚本执行结束 ---")
