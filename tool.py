import datetime
import pymongo
import re
import pytdx.hq as hq
from pytdx.params import TDXParams
from pytdx.config.hosts import hq_hosts as hosts

api = hq.TdxHq_API()


def log(log_info):
    """日志记录函数"""
    print(log_info)


def ping(ip, port):
    """测试ip连通时间"""
    tdx_api = hq.TdxHq_API()
    start = datetime.datetime.now()
    try:
        with tdx_api.connect(ip, port):
            log("F ping(): IP,%s port,%s" % (ip, port))
            if len(tdx_api.get_security_list(0, 1)) > 800:
                return datetime.datetime.now() - start
    except:
        log("F ping(): Bad response %s:%s" % (ip, port))
        return datetime.timedelta(9, 9, 0)


def select_best_server():
    """Select the best Server of TDX from pytdx.config.hosts"""
    log("Select the best Server of TDX from pytdx.config.hosts")
    time = [ping(x[1], x[-1]) for x in hosts[::]]
    log("===The best Server is : ")
    log(hosts[time.index(min(time))])
    return hosts[time.index(min(time))]


def get_companys(markets,server):
    """Get all company record from markets"""
    companys = []
    with api.connect(server[0],server[1]):
        for m in markets:
            for c in api.get_security_list(market=m,start=0):
                companys.append({'market':m,'code':c['code'],'name':c['name']})
    return companys

# get_companys([TDXParams.MARKET_SH],['117.34.114.27', 7709])

def get_companys_information(companys,server):
    """Get details for each company"""
    info = []
    with api.connect(server[0],server[1]):
        for cm in companys:
            for ct in api.get_company_info_category(cm['market'], cm['code']):
                # print(api.get_company_info_content(cm['market'], cm['code'],ct['filename'],ct['start'],ct['length']))
                info.append({'name':ct['name'],'length':ct['length'],'info':api.get_company_info_content(cm['market'], cm['code'],ct['filename'],ct['start'],ct['length'])})
    return info

# get_companys_information([{'code': '002496', 'name': '上证指数', 'market': 1}],['183.57.72.11', 7709])

tags = ["★本栏包括","】★","【","】"]
table_tags = ['┌(.*?)┐','└(.*?)┘','├(.*?)┤','｜',"【","】","★本栏包括","】★"]
def get_main_titles(info,tags=tags):
    """Get the title of each section
    @:param info:str,the data containing the main title
    @:param tags:list(4),list[0] Include the head of the tag header
                        ,list[1] Include the head of the tag tail
                        ,list[2] Header of the title
                        ,list[3] the end of the title tag
    """
    return re.findall("%s(.*?)%s"%(tags[2],tags[3])
                      ,info[info.find(tags[0])+len(tags[0]):info.find(tags[1])+len(tags[1]):])

def get_titles(info,tags):
    """Extract title from the data
    @:param info:str,the data containing the title
    @:param tags:list(2),list[0] Header of the title
                        ,list[1] the end of the title tag
    """
    return re.findall("%s(.*?)%s"%(tags[0],tags[1]),info)

def get_record(info,titles):
    return [info.find(t) for t in titles]

def additional_line(line):
    """Determine whether the current line is attached to the previous line
    @:param line:list[str,],each data array
    This method is performed as follows：
        First determine whether the first data is all spaces, if yes, return True
        Iterative access to the remaining data
            Data is empty or in accordance with a certain format, yes, then return True
            continue otherwise
        Finally False
    """
    if line[0].isspace():
        return True
    for x in line:
        if x.isspace() or re.match('^\s+[0-9]+$',x):
            return True
        else:
            continue
    return False

def multi_line_merge(lines,tag,T=True):
    """Multi-line data processing, for data belonging to the same line up and down the merger
    @:param lines:list[str,]，Multi-line data array, each element is the data of each line,
                each line of data format is as follows: tag data tag ... tag data tag
    @:param tag:char ,The delimiter for the data in each row,
                with the delimiter at each end of the line
    @:return buffer:list[str,], data format is as follows： data space data space ... space data
    This function is executed as follows:
        Divide the first data by the delimiter and get an array with the leading and trailing whitespace of each element removed
        Traverse the remaining data:
            If the data is attached to the previous data, the first element of each element of the data is appended to the corresponding element of the previous data
            Otherwise, remove the leading and trailing whitespace for each element of the stripe data and add a space in the header to the previous data
        Returns an array of one bit, with each element being the combined result string
    """
    buffer = [x.strip() for x in lines[0].split(tag)]
    buffer = buffer[1:len(buffer) - 1:]
    for x in lines[1::]:
        fragment = x.split(tag)[1::]
        if T and additional_line(fragment[:len(fragment)-1:]):
            for i in range(len(fragment)-1):
                buffer[i] += fragment[i].strip()
        else:
            for i in range(len(fragment)-1):
                buffer[i] += ' ' + fragment[i].strip()
    return buffer

def separate_table(table,tag):
    return re.split('%s'%(tag),table.strip())[::2]

def separate_multi_table(info,tags,T=True):
    """Separates the included form from the data
    and returns an array of the form with the head and tail of the form removed
    @:param info:str,the data containing the table
    @:param tags:list(2),list[0] the head of the form tag
                        ,list[1] the end of the form tag
    """
    if T:
        return [x[1] for x in re.findall('%s(.*?)%s' % (tags[0], tags[1]), info, re.S)]
    else:
        return [x for x in re.findall('%s(.*?)%s' % (tags[0], tags[1]), info, re.S)]

def separate_line(line,tag):
    return [x for x in line.split(tag)][1:-1:]

def separate_multi_line(lines):
    """Separate data by line
    Returns an array of data for each row
    """
    return [x for x in (lines.strip()).splitlines()]
def spearate_and_conversion(data,tag=' '):
    """
    Each element of an array of n rows by 1 column is separated
    by a tag into an array of m rows and n columns,
    and the m value is the number of partitions
    :param data: [[,]]
    :param tag: char
    :return: [[,],]
    """
    return line_conversion([x.split(tag) for x in data])


def line_conversion(lines):
    """Two-dimensional array of ranks conversion"""
    return list(list(i) for i in zip(*lines))

def conversion(lines):
    """Convert two-dimensional array to dictionary array
    @:param lines:list[[,],],list[0] Dictionary key array
                            ,list[1,] Dictionary value array

    @:return [{},]
    """
    result = []
    for x in lines[1::]:
        d = {}
        for i in range(0, len(x)):
            d[lines[0][i]] = x[i]
        result.append(d)
    return result

def format_table_company_overview(table,tags):
    tmp = []
    for x in separate_multi_table(table,tags[0:2:]):
        for y in separate_table(x,tags[2]):
            info = multi_line_merge(separate_multi_line(y),tags[3])
            for i in range(0,len(info),2):
                tmp.append({info[i]:info[i+1]})
    return tmp

def format_multi_table_affiliated_companies(info,tags):
    result = []
    for x in separate_multi_table(info, tags[0:2:]):
        for y in format_table_affiliated_companies(x,tags):
            result.append(y)
    return result

def format_table_affiliated_companies(table,tags):
    tmp = []
    for x in separate_table(table, tags[2]):
        tmp.append(multi_line_merge(separate_multi_line(x), tags[3]))
    result = [tmp[0]]
    for x in spearate_and_conversion(tmp[1]):
        result.append(x)
    return conversion(result)

def format_table_finacial_indicator(table,tags):
    """
    Extract data from the table
    :param table: str
    :param tags:list    ,list[0] the head of the form tag
                        ,list[1] the end of the form tag
                        ,list[2] Each part of the table separator
                        ,list[3] Element delimiter in line
    :return:[{},]
    """
    buffer = []
    for x in separate_table(table.strip(),tags[2]):
        tmp = []
        for y in multi_line_merge(separate_multi_line(x),tags[3]):
            tmp.append(y.split())
        for y in line_conversion(tmp):
            buffer.append(y)
    return conversion(line_conversion(buffer))

def format_multi_table_finacial_indicator(info,tags,has_tags=False):
    """
    Extract data from the table
    :param table: str
    :param tags:list    ,list[0] the head of the form tag
                        ,list[1] the end of the form tag
                        ,list[2] Each part of the table separator
                        ,list[3] Element delimiter in line
    :return:[{},]
    """
    tmp = []
    for x in separate_multi_table(info, tags[0:2:]):
        for y in format_table_finacial_indicator(x, tags):
            tmp.append(y)
    return tmp

def format_table_financial_analysis(info,tags):
    """Extract form information
    :param info: str
    :param tags: list   ,list[0] the head of the form tag
                        ,list[1] the end of the form tag
                        ,list[2] Each part of the table separator
                        ,list[3] Element delimiter in line
                        ,list[4] Header of the title
                        ,list[5] the end of the title tag
    :return: [{},]
    The main implementation is as follows:
        Get each subtitle in the data
        Get subparts based on subheadings and extract information
        Return the extracted information

    """
    titles = get_titles(info, tags[4:6:])
    record = get_record(info,titles)
    record.append(len(info))
    result = []
    for i in range(len(record)-1):
        result.append({titles[i]:
            format_multi_table_finacial_indicator(info[record[i]:record[i+1]:],tags)})
    return result

def format_table_central_analysis(table,tags):
    """Get the data from the ring analysis table"""
    table = separate_table(table, tags[2])
    keys = separate_line(table[1], tags[3])[1:]
    keys.insert(0, table[0].split(tags[3])[1].strip())
    value = separate_multi_line(table[2])
    tmp = [keys]
    for y in value:
        tmp.append([x.strip() for x in separate_line(y, tags[3])])
    return conversion(tmp)

def format_multi_table_central_analysis(info,tags):
    tmp = []
    for x in separate_multi_table(info,tags[0:2:]):
        for y in format_table_central_analysis(x,tags):
            tmp.append(y)
    return tmp

def format_table_restricted_circulation(table,tags):
    tmp = []
    for x in separate_table(table,tags[2]):
        tmp.append(multi_line_merge(separate_multi_line(x),tags[3]))
    return conversion(tmp)

def format_multi_table_restricted_circulation(info,tags):
    tmp = []
    for x in separate_multi_table(info, tags[0:2:]):
        for y in format_table_restricted_circulation(x, tags):
            tmp.append(y)
    return tmp

def format_table_capital_structure(table,tags):
    # print(table)tmp = [y for y in table[table.find('\n'):table.find(tags[0]):].split()]
    tmp = [[y for y in table[table.find('\n'):table.find(tags[0]):].split()]]
    for x in separate_multi_table(table,tags[0:2:],False):
        for y in separate_multi_line(x):
            tmp.append([z for z in y.split()])
    return conversion(line_conversion(tmp))

def format_financial_analysis(info,tags=table_tags):
    """Extract information from financial_analysis
    @:param info:str
    @:param tags:
    The main implementation is as follows:
        Get each subtitle in the header
        Get parts based on subheadings and extract information
        Return the extracted information
    """
    titles = get_main_titles(info)
    info = info[info.find(tags[7])::]
    record = []
    for t in titles:
        record.append(info.find(t))
    record.append(len(info))
    result = []
    for i in range(len(record)-2):
        result.append({titles[i]:format_table_financial_analysis(info[record[i]:record[i+1]:],tags)})
    result.append({titles[-1]:
        format_multi_table_central_analysis(info[record[-1]:record[len(titles)]],tags)})
    return result

def format_company_overview(info,tags=table_tags):
    """Extract information from company overview"""
    titles = get_main_titles(info)
    info = info[info.find(tags[7])::]
    record = get_record(info,titles)
    record.append(len(info))
    result = []
    for i in range(0,len(titles)-1):
        result.append({titles[i]:format_table_company_overview(info[record[i]:record[i+1]],tags)})
    result.append({titles[-1]:
                format_multi_table_affiliated_companies(info[record[-2]:record[-1]],tags)})
    return result

def format_capital_struct_research(info,tags):
    titles = get_main_titles(info)
    info = info[info.find(tags[7])::]
    record = get_record(info, titles)
    record.append(len(info))
    result = []
    table_tags = ['─────────────────────────────────────'
        ,'─────────────────────────────────────','\s+']
    result.append({titles[0]:
                format_table_capital_structure(info[record[0]:record[1]:], table_tags)})
    result.append({titles[1]:format_multi_table_finacial_indicator(info[record[1]:record[2]:], tags)})
    result.append({titles[2]: format_multi_table_restricted_circulation(info[record[2]:record[3]:], tags)})
    result.append({titles[3]:''})
    return result

def format_capital_operation(info,tags):

    title = get_main_titles(info)
    info = info[info.find(tags[7])::]

    record = get_record(info,title)
    record.append(len(info))
    result = []
    for i in range(0,len(title)):
        result.append({title[i]:
                format_multi_table_affiliated_companies(info[record[i]:record[i+1]:],tags)})
    return result

def format_table_executive_briefing(table,tags):
    tmp = []
    result = []
    for x in separate_table(table,tags[2]):
        tmp.append(x)
    for x in tmp[0:2:]:
        for y in separate_line(x, tags[3]):
            result.append(y.strip())
    result.append(multi_line_merge(separate_multi_line(tmp[2]),tags[3])[0].replace(' ',''))
    return result

def format_multi_table_executive_briefing(info,tags):
    result = []
    for x in separate_multi_table(info,tags[0:2]):
        for y in format_table_executive_briefing(x,tags):
            result.append(y)
    return result

def format_table_executive_list(info,tags):
    start = [x.start() for x in re.finditer(tags[2],info)][-1]
    end = [x.start() for x in re.finditer(tags[1],info)][0]
    result = []
    for x in separate_multi_table(info[:start:] + info[end::],tags):
        table = separate_table(x,tags[2])

        for y in table[1::]:
            for z in line_conversion([z.split() for z in multi_line_merge(separate_multi_line(y),tags[3])]):
                result.append(z)
        result.insert(0,[y.strip() for y in separate_line(table[0], tags[3])])
        # for y in multi_line_merge(separate_multi_line(x),tags[3]):
        #     print(y)
    # return format_multi_table_finacial_indicator(info[:start:] + info[end::],tags)
    return conversion(result)
def format_high_level_governance(info,tags):
    title = get_main_titles(info)
    info = info[info.find(tags[7])::]
    record = get_record(info, title)
    record.append(len(info))
    result = []
    for i in [0,2]:
        result.append({title[i]:
                           format_multi_table_affiliated_companies(info[record[i]:record[i + 1]:], tags)})
    result.insert(1,{title[1]: format_table_executive_list(info[record[1]:record[2]:], tags)})
    result.append({title[3]:format_multi_table_executive_briefing(info[record[3]:record[4]:], tags)})


    return result
def test():
    with api.connect('180.153.18.171',7709):
        # for x in format_financial_analysis(api.get_company_info_content(0,'000004','000004.txt',16327,23545)):
        #     print(x)
        # for x in format_company_overview(api.get_company_info_content(0, '000001', '000001.txt', 9555, 7683)):
        #     print(x)
        # for x in format_capital_struct_research(
        #         api.get_company_info_content(0, '000001', '000001.txt', 177647, 5327),table_tags):
        #     print(x)
        # for x in format_capital_operation(
        #         api.get_company_info_content(0, '000001', '000001.txt', 182974, 3289),table_tags):
        #     print(x)

        for x in format_high_level_governance(
                api.get_company_info_content(
                    0,'000002', '000002.txt', 538137, 29667),table_tags):
            print(x)
            pass
        for x in api.get_company_info_category(0,'000002'):
            print(x)
test()