#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AV Track Merger v2.0 - 主入口
"""

from gui import MainWindow


def main():
    """主函数"""
    # 创建并显示主窗口
    window = MainWindow()

    # 运行应用
    window.mainloop()


if __name__ == "__main__":
    main()
