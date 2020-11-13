from PlayerScraper import PlayerScraper
import pandas as pd

def BatchGetPlayerPageSource(year, ps, batchsize=10):
    ''' processes data for all players drafter from that year onwards '''
    df = ps.players_df

    df = df[df['From'] > year]
    links = df['Player_links'].values
    exec_scripts = [f'window.open("{link}");' for link in links]

    page_sources = dict.fromkeys(links)
    
    for i in range(0, len(exec_scripts), batchsize):
        exec_script = ''.join(exec_scripts[i:i+batchsize])
        ps.driver.execute_script(exec_script)
        
        while len(ps.driver.window_handles) > 1:
            ps.driver.switch_to.window(ps.driver.window_handles[-1])
            page_sources[links[i]] = ps.driver.page_source
            ps.driver.close()

        exec_script = None
        ps.driver.switch_to.window(ps.driver.window_handles[0])

    return page_sources, df['Player_links'].values

def get_tables(vals, tbl_id):
    try:
        return vals[tbl_id]
    except:
        pass

def process_adj_shooting(df):
    '''
    column names were player specific for adj shooting so changed
    '''

    columns = ['Season','Age','Team','Lg','Pos','G','MP',
    '\xa0',
 'FG_player Shooting %','2P_player Shooting %','3P_player Shooting %','eFG_player Shooting %',
 'FT_player Shooting %','TS_player Shooting %','FTr_player Shooting %','3PAr_player Shooting %',
 '\xa0',
 'FG_League Shooting %','2P_League Shooting %','3P_League Shooting %','eFG_League Shooting %',
 'FT_League Shooting %','TS_League Shooting %','FTr_League Shooting %','3PAr_League Shooting %',
 '\xa0',
 'FG+_League-Adjusted','2P+_League-Adjusted','3P+_League-Adjusted','eFG+_League-Adjusted',
 'FT+_League-Adjusted','TS+_League-Adjusted','FTr+_League-Adjusted','3PAr+_League-Adjusted',
 '\xa0',
 'FG Add','TS Add', 'Player_link']

    df.columns = columns
    return df

def BatchProcessPlayers(year, ps, batchsize = 10):

    page_sources, player_links = BatchGetPlayerPageSource(year, batchsize = batchsize, ps= ps)

    tables = [ps.extract_all_tables_for_player(source) for source in page_sources]

    joined_tables = dict.fromkeys(ps.table_ids)

    for i in range(len(tables)):

        for tbl_id in ps.table_ids:
            if tbl_id == 'adj-shooting':
                dfs = []
                if tbl_id in tables[i]:
                    dfs.append(process_adj_shooting(tables[i][tbl_id]))
                    
            else:
                dfs = [get_tables(vals =tables[i] , 
                                tbl_id = tbl_id) for i in range(len(tables))\
                    if tbl_id in tables[i]]
                
            if dfs:
                df = pd.concat(dfs)
                df['Player_link'] = player_links[i]
                joined_tables[tbl_id] = df

    return joined_tables




    



