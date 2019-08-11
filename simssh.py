import argparse

from ssh_engine import SSHEngine

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-hosts', '--hosts', required=True, type=str, help='path to the host file')
    parser.add_argument('-username', '--username', required=True, type=str, help='username')
    parser.add_argument('-password', '--password', required=True, type=str, help='password')
    cfg = vars(parser.parse_args())

    host_file = cfg['hosts']
    engine = SSHEngine(host_file, username=cfg['username'], password=cfg['password'], auto_close=False)
    # engine.upload_dir('/Users/hxssgaa/PycharmProjects/HelloPy', '/root/workspace/HelloPy')
    # pid = {}
    # engine.execute_commands(['ps -fC python3 | grep hello2'], lambda x: pid.update({x[0]: x[2].decode('utf-8').split()[1]}))
    # print(len(pid))
    # engine.execute_commands([{e: 'kill %s' % pid[e] for e in engine.hosts}], lambda x: print(x))
    engine.close_all()
    # engine.upload_dir('/Users/hxssgaa/Desktop/dddd', '/root/workspace/dddd')
