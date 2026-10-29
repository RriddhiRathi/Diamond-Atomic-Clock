"""Screen-only Plotly layout; numerical arrays and publication exporters are untouched."""
PALETTE = ['#38d2bd','#94baff','#f5bb65','#c5a0ff','#f28da8','#d7e0ed']
CHART_CONFIG = dict(displaylogo=False,scrollZoom=False,responsive=True,
                    toImageButtonOptions=dict(format='svg',filename='DiamondClock_SIMULATION'))


def scientific_plot(fig, *, height=430):
    fig.update_layout(template='plotly_dark',height=height,
        paper_bgcolor='#101722',plot_bgcolor='#101722',colorway=PALETTE,
        font=dict(family='Arial, sans-serif',size=12,color='#e6edf7'),
        margin=dict(l=65,r=20,t=48,b=105),
        title=dict(font=dict(size=14),x=0.02,xanchor='left'),
        legend=dict(orientation='h',x=0,y=-.08,yanchor='top',font=dict(size=11),
                    bgcolor='rgba(0,0,0,0)',maxheight=70),
        hoverlabel=dict(font_size=12))
    for axis in fig.select_xaxes():
        axis.update(title_font_size=12,tickfont_size=11,automargin=True,nticks=6,
                    gridcolor='#27364a',zerolinecolor='#506076')
    for axis in fig.select_yaxes():
        axis.update(title_font_size=12,tickfont_size=11,automargin=True,nticks=6,
                    gridcolor='#27364a',zerolinecolor='#506076')
        if axis.type=='log':axis.update(tickformat='.1e',exponentformat='e',showexponent='all')
    return fig


def crystal_style(fig):
    fig.update_layout(height=490,margin=dict(l=0,r=0,t=0,b=110),paper_bgcolor='#101722',
        font=dict(size=11,color='#e6edf7'),
        legend=dict(orientation='h',x=0,y=-.03,yanchor='top',font=dict(size=10),maxheight=90))
    return fig
