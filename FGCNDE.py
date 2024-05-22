class NL(nn.Module):
    def __init__(self):
        #in_c：输入维度  hid_c:隐藏层维度 out_c:输出维度
        super(NL,self).__init__()
        self.linear_1 = nn.LSTM(16, 32,num_layers =1,batch_first=True)
        self.linear_2 = nn.Linear(32, 16,bias=False)

        self.act1 = nn.Tanh()

    def forward(self,data): 
        B, N = data.size(0), data.size(1)
        data = data.view(B*N,1,16)
        out_1,_ = self.linear_1(data)
        out_1 = self.act1(out_1)        
        out_1 = self.linear_2(out_1).view(B,N,16)

        return out_1 
class GL(nn.Module):
    def __init__(self):
        #in_c：输入维度  hid_c:隐藏层维度 out_c:输出维度
        super(GL,self).__init__()
        self.out = nn.Linear(16,16,bias=False)
        self.fankui = nn.Linear(16,16,bias=False)
    
    def forward(self,data,graph): 
        out_1 = torch.matmul(graph,data)
        out_2 = self.fankui(data)
        out_3 = self.out(data)
        out_4 = self.out(out_1+out_2-out_3)
        return out_4 
import torch
import torch.nn as nn
import torch.nn.init as init


class ChebConv(nn.Module):
    """
    The ChebNet convolution operation.

    :param in_c: int, number of input channels.
    :param out_c: int, number of output channels.
    :param K: int, the order of Chebyshev Polynomial.
    """
    def __init__(self, in_c, out_c, K, bias=True, normalize=True):
        super(ChebConv, self).__init__()
        self.normalize = normalize

        self.weight = nn.Parameter(torch.Tensor(K + 1, 1, in_c, out_c))  # [K+1, 1, in_c, out_c]
        init.xavier_normal_(self.weight)

        if bias:
            self.bias = nn.Parameter(torch.Tensor(1, 1, out_c))
            init.zeros_(self.bias)
        else:
            self.register_parameter("bias", None)

        self.K = K + 1

    def forward(self, inputs, graph):
        """
        :param inputs: the input data, [B, N, C]
        :param graph: the graph structure, [N, N]
        :return: convolution result, [B, N, D]
        """
        L = ChebConv.get_laplacian(graph, self.normalize)  # [N, N]
        mul_L = self.cheb_polynomial(L).unsqueeze(1)   # [K, 1, N, N]
        result = torch.matmul(mul_L, inputs)  # [K, B, N, C]
        result = torch.matmul(result, self.weight)  # [K, B, N, D]
        result = torch.sum(result, dim=0) + self.bias  # [B, N, D]

        return result

    def cheb_polynomial(self, laplacian):
        """
        Compute the Chebyshev Polynomial, according to the graph laplacian.

        :param laplacian: the graph laplacian, [N, N].
        :return: the multi order Chebyshev laplacian, [K, N, N].
        """
        N = laplacian.size(0)  # [N, N]
        multi_order_laplacian = torch.zeros([self.K, N, N], device=laplacian.device, dtype=torch.float)  # [K, N, N]
        multi_order_laplacian[0] = torch.eye(N, device=laplacian.device, dtype=torch.float)

        if self.K == 1:
            return multi_order_laplacian
        else:
            multi_order_laplacian[1] = laplacian
            if self.K == 2:
                return multi_order_laplacian
            else:
                for k in range(2, self.K):
                    multi_order_laplacian[k] = 2 * torch.mm(laplacian, multi_order_laplacian[k-1]) - \
                                               multi_order_laplacian[k-2]

        return multi_order_laplacian

    @staticmethod
    def get_laplacian(graph, normalize):
        """
        return the laplacian of the graph.

        :param graph: the graph structure without self loop, [N, N].
        :param normalize: whether to used the normalized laplacian.
        :return: graph laplacian.
        """
        if normalize:
            D = torch.diag(torch.sum(graph, dim=-1) ** (-1 / 2))
            L = torch.eye(graph.size(0), device=graph.device, dtype=graph.dtype) - torch.mm(torch.mm(D, graph), D)
        else:
            D = torch.diag(torch.sum(graph, dim=-1))
            L = D - graph
        return L
from sklearn.metrics.pairwise import cosine_similarity
class ChebNet(nn.Module):
    def __init__(self):
        """
        :param in_c: int, number of input channels.
        :param hid_c: int, number of hidden channels.
        :param out_c: int, number of output channels.
        :param K:
        """
        super(ChebNet, self).__init__()
        self.node_embeddings = nn.Parameter(torch.rand(307,10))
#         self.A = graph
        self.conv = ChebConv(in_c=5, out_c=16, K=5, bias=True, normalize=True)
        self.cou = nn.Linear(5,16,bias=False)
        self.NL = NL()
        self.GL = GL()
        self.LSTM = nn.LSTM(input_size =16,hidden_size = 8,num_layers =1,batch_first=True)
        self.linear1 = nn.Linear(8, 1,bias=False) 
        self.act = nn.Tanh()
        self.weight = nn.Parameter(torch.Tensor(16,16))  # [K+1, 1, in_c, out_c]
        self.fankui = nn.Parameter(torch.Tensor(5,16))
        init.xavier_normal_(self.weight)
        self.LL = nn.Linear(3,8)
        self.LL1 = nn.Linear(8,16)




    def forward(self,data, A,device):
        graph_data =  torch.tensor(cosine_similarity(self.node_embeddings.cpu().detach().numpy())).cuda()
#         graph_data = self.A.to(device)
        flow_x = data["flow_x"].to(device).squeeze()  # [B,40,5,1]
        
        B, N = flow_x.size(0), flow_x.size(1)
        flow_x = flow_x.unsqueeze(3)
        I = torch.eye(N, dtype=graph_data.dtype).to(device)
        D = torch.diag(torch.sum(graph_data, dim=-1) ** (-1 / 2)).to(device)
        L = torch.eye(graph_data.size(0),  dtype=graph_data.dtype).to(device) - torch.mm(torch.mm(D, graph_data), D)#[N,N]
#         out = torch.matmul(L,flow_x.permute(0,2,1,3))#[N,N]*[B,T,D,n] --> [B,T,N,D]
#         output = self.LL(out.permute(0,2,1,3))#-->[B,N,T,8]
#         output = self.LL1(output).permute(0,2,1,3)#-->[B,T,N,16]
        out = self.cou(flow_x[:,:,:,0].squeeze())
        output = self.conv(flow_x[:,:,:,0].squeeze(),graph_data) #[B,N,16]
        res_1 = output+0.5*self.GL(output,L)+0.5*self.GL(out+2*self.GL(output,L),L)
        res_2 = res_1+0.5*self.GL(res_1,L)+0.5*self.GL(output+2*self.GL(res_1,L),L)
        res_3 = res_2+0.5*self.GL(res_2,L)+0.5*self.GL(res_1+2*self.GL(res_2,L),L)
        res_4 = res_3+0.5*self.GL(res_3,L)+0.5*self.GL(res_2+2*self.GL(res_3,L),L)
        res_5 = res_4+0.5*self.GL(res_4,L)+0.5*self.GL(res_3+2*self.GL(res_4,L),L)
        res_6 = res_5+0.5*self.GL(res_5,L)+0.5*self.GL(res_4+2*self.GL(res_5,L),L)
        res_7 = res_6+0.5*self.GL(res_6,L)+0.5*self.GL(res_5+2*self.GL(res_6,L),L)
        res_8 = res_7+0.5*self.GL(res_7,L)+0.5*self.GL(res_6+2*self.GL(res_7,L),L)
        step_0 = res_8+0.5*self.GL(res_8,L)+0.5*self.GL(res_7+2*self.GL(res_8,L),L)
        step_1 = step_0+0.5*self.GL(step_0,L)+0.5*self.GL(res_8+2*self.GL(step_0,L),L)
        
#         res_1 = output+0.1*torch.matmul((L-I),output) 
#         res_2 = res_1+0.1*torch.matmul((L-I),res_1)        
#         res_3 = res_2+0.1*torch.matmul((L-I),res_2)        
#         res_4 = res_3+0.1*torch.matmul((L-I),res_3)        
#         res_5 = res_4+0.1*torch.matmul((L-I),res_4)
#         res_6 = res_5+0.1*torch.matmul((L-I),res_5)        
#         res_7 = res_6+0.1*torch.matmul((L-I),res_6)        
#         res_8 = res_7+0.1*torch.matmul((L-I),res_7)
#         res_9 = res_8+0.1*torch.matmul((L-I),res_8)
#         res_0 = res_9+0.1*torch.matmul((L-I),res_9)  
#         step_0 = torch.matmul((res_1+res_2+res_3+res_4+res_5+res_6+res_7+res_8+res_9),self.weight) #[B,40,1,8]   
#         step_1 = torch.matmul((res_1+res_2+res_3+res_4+res_5+res_6+res_7+res_8+res_9+res_0),self.weight) #[B,40,1,8]   
        
        
        
        
        zero = torch.zeros(B,N,16).to(device)
        ceshi = self.NL(zero)
        V = 2*step_1*self.NL(step_1)
        gate = 0.1*torch.ones(B,N,16).to(device)
        
        
        guance_1 = 0.5*self.NL(step_1)+step_1+0.5*self.NL(step_0+2*self.NL(step_1))
        guance_2 = 0.5*self.NL(guance_1)+guance_1+0.5*self.NL(step_1+2*self.NL(guance_1))
        guance_3 = 0.5*self.NL(guance_2)+guance_2+0.5*self.NL(guance_1+2*self.NL(guance_2))
        guance_4 = 0.5*self.NL(guance_3)+guance_3+0.5*self.NL(guance_2+2*self.NL(guance_3))
        guance_5 = 0.5*self.NL(guance_4)+guance_4+0.5*self.NL(guance_3+2*self.NL(guance_4))
        guance_6 = 0.5*self.NL(guance_5)+guance_5+0.5*self.NL(guance_4+2*self.NL(guance_5))
        guance_7 =0.5*self.NL(guance_6)+guance_6+0.5*self.NL(guance_5+2*self.NL(guance_6))
        guance_8 = 0.5*self.NL(guance_7)+guance_7+0.5*self.NL(guance_6+2*self.NL(guance_7))
        guance_9 = 0.5*self.NL(guance_8)+guance_8+0.5*self.NL(guance_7+2*self.NL(guance_8))
        guance_10 = 0.5*self.NL(guance_9)+guance_9+0.5*self.NL(guance_8+2*self.NL(guance_9))     
        padding = torch.stack((guance_1,guance_2,guance_3,guance_4,guance_5,guance_6,guance_7,guance_8,guance_9,guance_10),dim=2)#[B,N,10,16]
        
        output_1,_ = self.LSTM(padding.view(-1,10,16))  #[B*N,10,8]
        pre = self.linear1(output_1).view(B,N,10)      

        return pre,zero,ceshi,V,gate,res_1,res_2,res_3,res_4,res_5,res_6,res_7,res_8,step_0,step_1,output,graph_data,L