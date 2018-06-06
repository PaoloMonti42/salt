import gdb, json

#in order to work with per-cpu variables, we need to resolve some addresses
#assuming we are working on a mono-cpu system, anyways
cpu0_offset = gdb.lookup_global_symbol('__per_cpu_offset').value()[0]  
current_task_offset = gdb.lookup_global_symbol('current_task').value().address
current_task_ptr_ptr = cpu0_offset/8 + current_task_offset  #the /8 is to account for pointer arithmetic, <struct task_struct **> has size 8

filter_on = False
proc_filter = set()
cache_filter = set()
record_on = False
history = list()
filter_rel = "or"


def get_task_info():
  """
  obtain information about the current task
  returns name and PID, but can be easily customized
  """
  current = current_task_ptr_ptr.dereference().dereference()
  name = current['comm'].string()
  pid = int(current['pid'])
  return (name, pid)   

def tohex(val, nbits):
  """
  convenience function to pretty-print hexadecimal numbers as unsigned and on a given amount of bits
  """
  return hex((val + (1 << nbits)) % (1 << nbits))

def apply_filter(proc, cache):
  """
  apply current filtering rules on the given item
  depending on the chosen relationship. the conditions can be combined as AND or OR
  """
  if filter_on: 
    if filter_rel == 'or':
      if proc in proc_filter or cache in cache_filter:
        return True
    else: 
      if proc in proc_filter and cache in cache_filter:
        return True
  else:
    return True
  return False

#compute at runtime the offset of the 'list' field in 'kmem_cache' structs    
list_offset = [f.bitpos for f in gdb.lookup_type('struct kmem_cache').fields() if f.name == 'list'][0] 

def get_next_cache(c1):
  """
  given a certain kmem cache, retrieve the memory area relative to the next one
  the code nagivates the struct, computes the address of 'next', then casts it to the correct type
  """
  nxt = c1['list']['next']
  c2 = gdb.Value(int(nxt)-list_offset//8).cast(gdb.lookup_type('struct kmem_cache').pointer())
  return c2
  
salt_caches = []

def walk_caches():
  """
  walk through all the active kmem caches and collect information about them 
  this function fills a data structure, used later by the other walk_* functions
  """
  global salt_caches
  salt_caches = []
  
  slab_caches = gdb.lookup_global_symbol('slab_caches').value().address
  salt_caches.append(dict())
  salt_caches[-1]['name'] = 'slab_caches'

  start = gdb.Value(int(slab_caches)-list_offset//8).cast(gdb.lookup_type('struct kmem_cache').pointer())
  nxt = get_next_cache(start)
  salt_caches[-1]['next'] = tohex(int(nxt), 64)
  salt_caches.append(dict())
  while True:
    objsize = int(nxt['object_size'])
    salt_caches[-1]['objsize'] = objsize
    offset = int(nxt['offset'])
    salt_caches[-1]['offset'] = offset
    salt_caches[-1]['name'] = nxt['name'].string()
    cpu_slab_offset = int(nxt['cpu_slab'])
    cpu_slab_ptr = gdb.Value(cpu_slab_offset+cpu0_offset).cast(gdb.lookup_type('struct kmem_cache_cpu').pointer())
    cpu_slab = cpu_slab_ptr.dereference()
    free = int(cpu_slab['freelist'])
    salt_caches[-1]['first_free'] = tohex(free, 64)
    salt_caches[-1]['freelist'] = []
    while free:
      free = gdb.Value(free+offset).cast(gdb.lookup_type('uint64_t').pointer()).dereference()
      salt_caches[-1]['freelist'].append(tohex(int(free), 64))
    nxt = get_next_cache(nxt)
    salt_caches[-1]['next'] = tohex(int(nxt), 64)
    if start == nxt:
      break
    else:
      salt_caches.append(dict())

def walk_caches_json(targets):
  """
  display the state of the target caches in JSON format
  if some cache names are specified, the rest will be filtered out
  """
  walk_caches()
  ret = "[\n"
  ret += json.dumps(salt_caches[0])+',\n'
  for c in salt_caches[1:]:
    if targets == None or c['name'] in targets:
      ret += json.dumps(c)+',\n'
  ret = ret[:-2] + "\n]\n"
  #g = open('graph.json', 'w') #XXX
  gdb.write(ret)
  #g.close()


def walk_caches_html(targets):
  """
  display the state of the target caches in html format
  if some cache names are specified, the rest will be filtered out
  """
  walk_caches()
  
  #g = open('graph.html', 'w') #XXX
  g = gdb
  g.write("""<html> <body> <style> th, .mytd { padding:10px; border: 1px solid black; border-collapse: collapse; } th { text-align:center; } </style>\n\n""")

  g.write("""<table width="300px">
<tr><th colspan="4">slab_caches</th></tr>
</table>\n\t\t\t\t\t\t<br></br>\n""")
  for n,c in enumerate(salt_caches[1:]):
    if (targets == None or c['name'] in targets) and len(c['freelist']) == 0:
      g.write("""<table width="300px">
<tr><th colspan="4">{}</th></tr>
<tr><td class="mytd">size</td><td class="mytd">{}</td><td class="mytd">offset</td><td class="mytd">{}</td></tr>
<tr><td class="mytd">freelist</td><td class="mytd" colspan="3">{}</td></tr>
<tr><td class="mytd">next</td><td class="mytd" colspan="3">{}</td></tr>
</table>\n\t\t\t\t\t\t<br></br>\n""".format(c['name'], c['objsize'], c['offset'], c['first_free'], c['next']))
    elif (targets == None or ['name'] in targets) and len(c['freelist']) > 0:
      g.write("""<table><tr><td>
<table width="300px">
<tr><th colspan="4">{}</th></tr>
<tr><td class="mytd">size</td><td class="mytd">{}</td><td class="mytd">offset</td><td class="mytd">{}</td></tr>
<tr><td class="mytd">freelist</td><td class="mytd" colspan="3">{}</td></tr>
<tr><td class="mytd">next</td><td class="mytd" colspan="3">{}</td></tr>
</table></td>
<td><table width="50px"><tr><button title="Click to show/hide content" type="button" onclick="if(document.getElementById('spoiler{}') .style.display=='none') {{document.getElementById('spoiler{}') .style.display=''}}else{{document.getElementById('spoiler{}') .style.display='none'}}">Show/hide freelist</button>
</tr></table></td>
<td><div id="spoiler{}" style="display:none">
<table>""".format(c['name'], c['objsize'], c['offset'], c['first_free'], c['next'], n, n, n, n))
      for f in c['freelist']:
        g.write('\n<td class="mytd">{}</td>'.format(f))
      g.write("\n</table></div></td></tr></table>\n\t\t\t\t\t\t<br></br>\n")

  g.write("\n\n</body></html>\n")
  #g.close()

def walk_caches_stdout(targets):
  """
  display the state of the target caches in a human friendly format 
  if some cache names are specified, the rest will be filtered out
  """
  walk_caches()
  
  print(' ', '-'*14)
  print(' |', ' '*11, '|')
  print(' |        slab_caches')
  print(' |', ' '*11, '|')
  if targets != None:
    print(' |', ' '*10, '...')
    print(' |', ' '*11, '|')
  print(' |', ' '*11, 'v')
  for c in salt_caches[1:]:
    if targets == None or c['name'] in targets:
      print(' |   name:', c['name'])
      print(' |   fist_free:', c['first_free'])
      if len(c['freelist']) > 0:
        print(' |   freelist: ', c['freelist'][0])
      for f in c['freelist'][1:]:
        print(' |', ' '*12, f)
      print(' |   next:', c['next'])
      print(' |', ' '*11, '|')
      if targets != None:
        print(' |', ' '*10, '...')
      print(' |', ' '*11, '|')
      print(' |', ' '*11, 'v')
  print('  <' + '-'*13)

#returned in case of size 0 allocation requests
ZERO_SIZE_PTR = 0x10 

class kmallocSlabFinishBP(gdb.FinishBreakpoint):

  def stop(self):
    name, pid = get_task_info()  

    ret = self.return_value
    if ret == ZERO_SIZE_PTR:
      if apply_filter(name, -1):
        trace_info = 'kmalloc has been called with argument size=0 by process "' + name + '", pid ' + str(pid)
        print(trace_info)
      return False

    cache = ret['name'].string()

    if apply_filter(name, cache):
      trace_info = 'kmalloc is accessing cache ' + cache  + ' on behalf of process "' + name + '", pid ' + str(pid)
      print(trace_info)
      history.append(('kmalloc', cache, name, pid))

    return False  

flag = 0
class kmallocSlabBP(gdb.Breakpoint):

  def stop(self):
    global flag
    if flag == 1:
      kmallocSlabFinishBP(internal=True)
      flag = 0

class kmallocBP(gdb.Breakpoint):

  def stop(self):
    global flag
    flag = 1
    #kmallocSlabBP('kmalloc_slab', internal=True, temporary=True)



class kfreeFinishBP(gdb.FinishBreakpoint):

  def stop(self):
    rdi = gdb.selected_frame().read_register('rdi') #XXX
    return False
    if rdi == 0 or rdi == ZERO_SIZE_PTR or rdi == 0x40000000: #XXX
      return False

    cache = rdi.cast(gdb.lookup_type('struct kmem_cache').pointer()).dereference()
    cache = cache['name'].string()

    name, pid = get_task_info()  

    if apply_filter(name, cache):
      trace_info = 'kfree is freeing an object from cache ' + cache  + ' on behalf of process "' + name + '", pid ' + str(pid)
      print(trace_info)
      history.append(('kfree', cache, name, pid))
    return False

class kfreeBP(gdb.Breakpoint):

  def stop(self):
    kfreeFinishBP(internal=True) 
    #x = gdb.selected_frame().read_var('x')
    #trace_info = 'freeing object at address ' + str(x)
    return False


class kmemCacheAllocBP(gdb.Breakpoint):

  def stop(self):
    s = gdb.selected_frame().read_var('s')

    name, pid = get_task_info()  
    cache = s['name'].string()

    if apply_filter(name, cache):
      trace_info = 'kmem_cache_alloc is accessing cache ' + cache  + ' on behalf of process "' + name + '", pid ' + str(pid)
      #trace_info += '\nreturning object at address ' + str(tohex(ret, 64))
      print(trace_info)
      history.append(('kmem_cache_alloc', cache, name, pid))
    
    return False


class kmemCacheFreeBP(gdb.Breakpoint):

  def stop(self):
    s = gdb.selected_frame().read_var('s')
    x = gdb.selected_frame().read_var('x')

    name, pid = get_task_info()  
    cache = s['name'].string()

    if apply_filter(name, cache):
      trace_info = 'kmem_cache_free is freeing from cache ' + cache  + ' on behalf of process "' + name + '", pid ' + str(pid)
      #trace_info += '\nfreeing object at address ' + str(x)
      print(trace_info)
      history.append(('kmem_cache_free', cache, name, pid))
    
    return False

class newSlabBP(gdb.Breakpoint):
  
  def stop(self):
    s = gdb.selected_frame().read_var('s')
    name, pid = get_task_info()  
    cache = s['name'].string()

    if apply_filter(name, cache):
      trace_info = 'a new slab is being created for ' + cache  + ' on behalf of process "' + name + '", pid ' + str(pid)
      print(trace_info)
      history.append(('new_slab', cache, name, pid))
    
    return False
  

class salt (gdb.Command):     

  def __init__ (self):
    super (salt, self).__init__ ("salt", gdb.COMMAND_USER)
    kmallocBP('__kmalloc', internal=True)
    kmallocSlabBP('kmalloc_slab', internal=True)
    kfreeBP('kfree')
    kmemCacheAllocBP('kmem_cache_alloc', internal=True)
    kmemCacheFreeBP('kmem_cache_free', internal=True)
    newSlabBP('new_slab', internal=True)
  
  def invoke (self, arg, from_tty):
    if not arg:
      print('Missing option. Type \"salt help\" for more information.')  
    else:
      global filter_on
      global proc_filter
      global cache_filter
      global filter_rel
      global record_on
      global history

      args = arg.split()
      if args[0] == 'filter':

        if len(args)<2:
          print('Missing option. Valid arguments are: enable, disable, status, add, remove.') 

        elif args[1] == 'enable':
          filter_on = True
          print('Filtering enabled.')

        elif args[1] == 'disable':
          filter_on = False
          print('Filtering disbled.')

        elif args[1] == 'status':
          if filter_on:
            print('Filtering is on.')
            print('Tracing information will be displayed for the following processes: ' + ', '.join(proc_filter))
            print('Tracing information will be displayed for the following caches: ' + ', '.join(cache_filter))
            print('Subfilter relation is set to ' + filter_rel.upper() + '.')
          else:
            print('Filtering is off.')

        elif args[1] == 'add':
          if len(args)<3:
            print('Missing option. Valid arguments are: process, cache.') 
          elif args[2] == 'process':
            for name in args[3:]:
              proc_filter.add(name)  
              print("Added '"+ name +"' to filtered processes.")
          elif args[2] == 'cache':
            for name in args[3:]:
              cache_filter.add(name)  
              print("Added '"+ name +"' to filtered caches.")
          else:
            print('Invalid option. Valid arguments are: process, cache.')  

        elif args[1] == 'remove':
          if len(args)<3:
            print('Missing option. Valid arguments are: process, cache.') 
          elif args[2] == 'process':
            for name in args[3:]:
              try:
                proc_filter.remove(name)  
                print("Removed '"+ name +"' from filtered processes.")
              except:
                print("'"+ name +"' is not among filtered processes.")
          elif args[2] == 'cache':
            for name in args[3:]:
              try:
                cache_filter.remove(name)  
                print("Removed '"+ name +"' from filtered processes.")
              except:
                print("'"+ name +"' is not among filtered processes.")
          else:
            print('Invalid option. Valid arguments are: process, cache.')  

        elif args[1] == 'relation':
          if len(args)<3:
            print('Missing option. Valid arguments are: OR, AND.') 
          elif args[2].lower() == 'or':
            filter_rel = 'or'
            print('Subfilter relation set to OR.')
          elif args[2].lower() == 'and':
            filter_rel = 'and'
            print('Subfilter relation set to AND.')
          else:
            print('Invalid option. Valid arguments are: OR, AND.')  

        else:
          print('Invalid option. Valid arguments are: enable, disable, status, add, remove, relation.') 

      elif args[0] == 'record':

        if len(args)<2:
          print('Missing option. Valid arguments are: on, off, show, clear.') 

        elif args[1] == 'on':
          record_on = True
          print('Recording enabled.')

        elif args[1] == 'off':
          record_on = False
          print('Recording disabled.')

        elif args[1] == 'show':
          for event in history:
            print(event)

        elif args[1] == 'clear':
          history = list()

        else:
          print('Invalid option. Valid arguments are: on, off, show, clear.') 

      elif args[0] == 'trace': 
        filter_on = True
        proc_filter = set()
        cache_filter = set()
        for name in args[1:]:
          proc_filter.add(name)  
        record_on = True
        history = list()
        print('Tracing enabled.')

      elif args[0] == 'walk': 
        if len(args)>1:
          walk_caches_stdout(args[1:])
        else:
          walk_caches_stdout(None)

      elif args[0] == 'walk_html': 
        if len(args)>1:
          walk_caches_html(args[1:])
        else:
          walk_caches_html(None)

      elif args[0] == 'walk_json': 
        if len(args)>1:
          walk_caches_json(args[1:])
        else:
          walk_caches_json(None)

      elif args[0] == 'help': 
        print('Possible commands:')
        print('\nfilter -- manage filtering features by adding with one of the following arguments')
        print('       enable -- enable filtering. Only information about filtered processes will be displayed')
        print('       disable -- disable filtering. Information about all processes will be displayed.')
        print('       status -- display current filtering parameters')
        print('       add process/cache <arg>-- add one or more filtering conditions')
        print('       remove process/cache <arg>-- remove one or more filtering conditions')
        print('       relation -- change how the two filters are combined. The default is OR')
        print('              OR -- an event is selected if it satisfied one filter OR the other')
        print('              AND -- an event is selected if it satisfied one filter AND the other')
        print('\nrecord -- manage recording features by adding with one of the following arguments')
        print('       on -- enable recording. Information about filtered processes will be added to the history')
        print('       off -- disable recording.')
        print('       show -- display the recorded history')
        print('       clear -- delete the recorded history')
        print('\ntrace <proc name> -- reset all filters and configure filtering for a specific process')
        print('\nwalk -- navigate all active caches and print relevant information')
        print('\nwalk_html -- navigate all active caches and generate relevant information in html format')
        print('\nwalk_json -- navigate all active caches and generate relevant information in json format')
        print('\nhelp -- display this message')
      else:
        print('Invalid option. Type \"salt help\" for more information.')  

  def complete(self, text, word):
    ret = []
    if text == word:
      for w in ['filter', 'record', 'trace', 'walk', 'walk_html', 'walk_json', 'help']:
        if word == w[:len(word)]:
          ret.append(w)

    else:
      comm = text.split()[0]
      if comm == 'filter':
        if len(text.split())==1 or text.split()[1] not in ['enable', 'disable', 'status', 'add', 'remove', 'relation']:
          for w in ['enable', 'disable', 'status', 'add', 'remove', 'relation']:
            if word == w[:len(word)]:
              ret.append(w)
        else:
          if len(text.split())==3 and word == '':
            return ret 
          comm = text.split()[1]
          if comm == 'add' or comm == 'remove':
            for w in ['process', 'cache']:
              if word == w[:len(word)]:
                ret.append(w)
          elif comm == 'relation':
            for w in ['OR', 'AND']:
              if word == w[:len(word)]:
                ret.append(w)
            
      elif comm == 'record':
        for w in ['on', 'off', 'show', 'clear']:
          if word == w[:len(word)]:
            ret.append(w)
      
    return ret

salt()


